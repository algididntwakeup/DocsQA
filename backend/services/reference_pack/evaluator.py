"""Deterministic rule evaluator for reference standards packs."""

from __future__ import annotations

import multiprocessing
import re
import threading
from typing import TYPE_CHECKING, Any

from schemas.issues import BoundingBox
from schemas.reference_pack import (
    NumericLimitParameters,
    RangeParameters,
    ReferenceFinding,
    ReferenceRule,
    RequiredReferenceParameters,
    RuleDefinition,
    RuleEvaluationResult,
    RuleEvaluationStatus,
    RuleType,
    TerminologyParameters,
    UnitParameters,
)

if TYPE_CHECKING:
    from schemas.extraction import ExtractionArtifact

# Regex sandbox limits (custom packs may contain untrusted patterns).
REGEX_TIMEOUT_SECONDS = 0.1
# Spawn startup (interpreter + imports) is not bounded by REGEX_TIMEOUT_SECONDS;
# only actual regex execution is. Ping-wait uses this budget instead.
SANDBOX_STARTUP_SECONDS = 10.0
MAX_RULES_PER_RUN = 500


class RegexTimeoutError(Exception):
    """Raised when a pattern exceeds the sandboxed execution budget (possible ReDoS)."""


# ponytail: thread-based timeouts cannot work here — CPython's re.search holds
# the GIL for the whole C-level match, so the parent starves and join() never
# returns. A subprocess can be terminated mid-C-call. Upgrade path: if a future
# CPython exposes per-call regex cancellation (or we adopt the `regex` module),
# drop the worker process entirely.


class SandboxMatch:
    """Lightweight stand-in for ``re.Match`` reconstructed from worker data."""

    __slots__ = ("_span", "_string", "_groups")

    def __init__(self, string: str, groups: tuple[str | None, ...], span: tuple[int, int]) -> None:
        self._string = string
        self._groups = groups
        self._span = span

    def group(self, index: int = 0) -> str:
        value = self._groups[index]
        return value if value is not None else ""

    def groups(self) -> tuple[str | None, ...]:
        return self._groups

    def start(self) -> int:
        return self._span[0]

    def end(self) -> int:
        return self._span[1]

    @property
    def lastindex(self) -> int | None:
        return None if len(self._groups) <= 1 else len(self._groups) - 1


def _sandbox_child(conn: multiprocessing.connection.Connection) -> None:  # pragma: no cover
    """Worker loop: receives (pattern, text, flags), replies (status, span, groups)."""
    while True:
        try:
            message = conn.recv()
        except (EOFError, KeyboardInterrupt, OSError):
            return
        if message[0] == "__ping__":
            conn.send(("__pong__", None, None))
            continue
        pattern, text, flags = message
        try:
            match = re.compile(pattern, flags).search(text)
        except Exception:  # noqa: BLE001 - a crashing pattern must not escape the sandbox
            conn.send(("error", None, None))
            continue
        if match is None:
            conn.send(("none", None, None))
        else:
            conn.send(("match", match.span(), (match.group(0),) + match.groups()))


class _RegexSandbox:
    """Persistent regex worker subprocess guarded by a wall-clock timeout.

    One worker is reused across calls; on timeout it is terminated (killing the
    runaway C-level match via TerminateProcess) and lazily respawned.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ctx = multiprocessing.get_context("spawn")
        self._parent: Any = None
        self._process: Any = None

    def _start(self) -> Any:
        self._stop()
        parent, child = self._ctx.Pipe()
        proc = self._ctx.Process(target=_sandbox_child, args=(child,), daemon=True)
        proc.start()
        child.close()
        self._parent, self._process = parent, proc
        return parent

    def _ping(self, parent: Any) -> bool:
        """Confirm the freshly spawned worker is alive (spawn startup is slow on Windows)."""
        parent.send(("__ping__", "", 0))
        if not parent.poll(timeout=SANDBOX_STARTUP_SECONDS):
            return False
        return bool(parent.recv()[0] == "__pong__")

    def _stop(self) -> None:
        if self._process is not None:
            if self._process.is_alive():
                self._process.terminate()
            self._process.join(timeout=1)
            self._process.close()
        if self._parent is not None:
            self._parent.close()
        self._parent, self._process = None, None

    def search(
        self,
        compiled: re.Pattern[str],
        text: str,
        timeout: float,
    ) -> re.Match[str] | SandboxMatch | None:
        with self._lock:
            fresh = not (self._process and self._process.is_alive())
            parent = self._start() if fresh else self._parent
            assert parent is not None
            if fresh and not self._ping(parent):
                self._stop()
                raise RegexTimeoutError("Sandbox worker failed to start")
            parent.send((compiled.pattern, text, compiled.flags))
            if parent.poll(timeout):
                status, span, groups = parent.recv()
                if status == "match":
                    return SandboxMatch(text, groups, span)
                if status in ("none", "error"):
                    return None
                raise RegexTimeoutError("Evaluation timeout (possible ReDoS)")
            # Worker is stuck inside the C-level match: kill it hard.
            self._stop()
            raise RegexTimeoutError("Evaluation timeout (possible ReDoS)")

    def shutdown(self) -> None:
        with self._lock:
            self._stop()


_sandbox = _RegexSandbox()


def sandboxed_search(
    pattern: str | re.Pattern[str],
    text: str,
    timeout: float = REGEX_TIMEOUT_SECONDS,
    flags: int = 0,
) -> re.Match[str] | SandboxMatch | None:
    """Run ``pattern.search(text)`` under a wall-clock timeout guard.

    Malicious or accidentally catastrophic patterns (ReDoS) are killed after
    ``timeout`` seconds; callers should treat that as an UNRESOLVED evaluation.
    """
    try:
        compiled = re.compile(pattern, flags) if isinstance(pattern, str) else pattern
    except re.error:
        return None
    return _sandbox.search(compiled, text, timeout)


class ReferenceRuleEvaluator:
    """Evaluates reference rules against extracted text spans or raw text documents."""

    def __init__(self, rules: list[ReferenceRule]) -> None:
        self.rules = rules

    def evaluate_text(
        self,
        text: str,
        page_number: int = 1,
    ) -> list[ReferenceFinding]:
        """Evaluate all active rules against raw document text."""
        findings: list[ReferenceFinding] = []
        for rule in self.rules:
            if rule.kind == "range" and rule.range_params:
                findings.extend(
                    self._eval_range(rule, rule.range_params, text, page_number)
                )
            elif rule.kind == "unit" and rule.unit_params:
                findings.extend(
                    self._eval_unit(rule, rule.unit_params, text, page_number)
                )
            elif rule.kind == "numeric_limit" and rule.numeric_limit_params:
                findings.extend(
                    self._eval_numeric_limit(rule, rule.numeric_limit_params, text, page_number)
                )
            elif rule.kind == "terminology" and rule.terminology_params:
                findings.extend(
                    self._eval_terminology(rule, rule.terminology_params, text, page_number)
                )
            elif rule.kind == "required_reference" and rule.required_reference_params:
                findings.extend(
                    self._eval_required_reference(
                        rule, rule.required_reference_params, text, page_number
                    )
                )
        return findings

    def evaluate_artifact(
        self,
        artifact: ExtractionArtifact,
    ) -> list[ReferenceFinding]:
        """Evaluate rules across an extracted PDF document artifact."""
        # Group text spans by page
        pages: dict[int, list[str]] = {}
        for span in artifact.spans:
            p = span.bbox.page_index + 1
            pages.setdefault(p, []).append(span.text)
        for heading in artifact.headings:
            p = heading.bbox.page_index + 1
            pages.setdefault(p, []).append(heading.text)

        all_findings: list[ReferenceFinding] = []
        full_text_combined = " ".join(" ".join(lines) for lines in pages.values())

        for p, lines in sorted(pages.items()):
            page_text = "\n".join(lines)
            # Evaluate range, unit, numeric_limit, and terminology per page
            for rule in self.rules:
                if rule.kind == "range" and rule.range_params:
                    all_findings.extend(
                        self._eval_range(rule, rule.range_params, page_text, p)
                    )
                elif rule.kind == "unit" and rule.unit_params:
                    all_findings.extend(
                        self._eval_unit(rule, rule.unit_params, page_text, p)
                    )
                elif rule.kind == "numeric_limit" and rule.numeric_limit_params:
                    all_findings.extend(
                        self._eval_numeric_limit(rule, rule.numeric_limit_params, page_text, p)
                    )
                elif rule.kind == "terminology" and rule.terminology_params:
                    all_findings.extend(
                        self._eval_terminology(rule, rule.terminology_params, page_text, p)
                    )

        # Evaluate required_reference across the entire document
        for rule in self.rules:
            if rule.kind == "required_reference" and rule.required_reference_params:
                all_findings.extend(
                    self._eval_required_reference(
                        rule, rule.required_reference_params, full_text_combined, 1
                    )
                )

        return self._deduplicate(all_findings)

    def _create_finding(
        self,
        rule: ReferenceRule,
        message: str,
        recommendation: str,
        detected_fact: str,
        detected_parameter: str | None,
        detected_value: str | None,
        page_number: int,
    ) -> ReferenceFinding:
        compliance_status = (
            "UNRESOLVED"
            if rule.requires_engineering_judgement
            else rule.default_status
        )
        return ReferenceFinding(
            rule_id=rule.rule_id,
            standard=rule.standard,
            edition=rule.edition,
            clause=rule.clause,
            standard_page=rule.standard_page,
            rule_kind=rule.kind,
            severity=rule.severity,
            message=message,
            recommendation=recommendation,
            detected_fact=detected_fact,
            detected_parameter=detected_parameter,
            detected_value=detected_value,
            compliance_status=compliance_status,
            page_number=page_number,
        )

    # ── Rule Kind Evaluators ──────────────────────────────────────────

    def _eval_range(
        self,
        rule: ReferenceRule,
        params: RangeParameters,
        text: str,
        page_number: int,
    ) -> list[ReferenceFinding]:
        findings: list[ReferenceFinding] = []
        try:
            pattern = re.compile(params.pattern, re.IGNORECASE)
        except re.error:
            return []

        for match in pattern.finditer(text):
            val_str = match.group(1) if match.groups() else match.group(0)
            try:
                val = float(val_str.replace(",", ""))
            except ValueError:
                continue

            unit = match.group(2) if len(match.groups()) >= 2 else ""
            unit_suffix = f" {unit}".rstrip()

            violates = False
            if params.min_value is not None:
                violates_min = (
                    val < params.min_value if params.inclusive_min else val <= params.min_value
                )
                if violates_min:
                    violates = True

            if params.max_value is not None:
                violates_max = (
                    val > params.max_value if params.inclusive_max else val >= params.max_value
                )
                if violates_max:
                    violates = True

            if violates:
                min_repr = params.min_value if params.min_value is not None else "-∞"
                max_repr = params.max_value if params.max_value is not None else "+∞"
                fact = (
                    f"{params.parameter_name} of {val}{unit_suffix} is outside "
                    f"permitted standard range [{min_repr}, {max_repr}]."
                )
                msg = rule.message_template.format(
                    parameter=params.parameter_name,
                    value=val,
                    unit=unit,
                    clause=rule.clause,
                ) if "{" in rule.message_template else rule.message_template
                rec = rule.recommendation_template.format(
                    parameter=params.parameter_name,
                    min_val=params.min_value,
                    max_val=params.max_value,
                    clause=rule.clause,
                ) if "{" in rule.recommendation_template else rule.recommendation_template

                findings.append(
                    self._create_finding(
                        rule=rule,
                        message=msg,
                        recommendation=rec,
                        detected_fact=fact,
                        detected_parameter=params.parameter_name,
                        detected_value=str(val),
                        page_number=page_number,
                    )
                )
        return findings

    def _eval_unit(
        self,
        rule: ReferenceRule,
        params: UnitParameters,
        text: str,
        page_number: int,
    ) -> list[ReferenceFinding]:
        findings: list[ReferenceFinding] = []
        try:
            pattern = re.compile(params.pattern, re.IGNORECASE)
        except re.error:
            return []

        allowed_lower = {u.lower() for u in params.allowed_units}
        forbidden_lower = {u.lower() for u in params.forbidden_units}

        for match in pattern.finditer(text):
            detected_unit = match.group(1).strip() if match.groups() else ""
            if not detected_unit:
                continue

            detected_lower = detected_unit.lower()
            is_forbidden = detected_lower in forbidden_lower
            is_not_allowed = detected_lower not in allowed_lower

            if is_forbidden or is_not_allowed:
                fact = (
                    f"Non-standard or forbidden unit '{detected_unit}' used for "
                    f"{params.parameter_name}."
                )
                msg = rule.message_template.format(
                    parameter=params.parameter_name,
                    unit=detected_unit,
                    clause=rule.clause,
                ) if "{" in rule.message_template else rule.message_template
                rec = rule.recommendation_template.format(
                    parameter=params.parameter_name,
                    canonical=params.canonical_unit,
                    allowed=", ".join(params.allowed_units),
                    clause=rule.clause,
                ) if "{" in rule.recommendation_template else rule.recommendation_template

                findings.append(
                    self._create_finding(
                        rule=rule,
                        message=msg,
                        recommendation=rec,
                        detected_fact=fact,
                        detected_parameter=params.parameter_name,
                        detected_value=detected_unit,
                        page_number=page_number,
                    )
                )
        return findings

    def _eval_numeric_limit(
        self,
        rule: ReferenceRule,
        params: NumericLimitParameters,
        text: str,
        page_number: int,
    ) -> list[ReferenceFinding]:
        findings: list[ReferenceFinding] = []
        if params.context_pattern and not re.search(params.context_pattern, text, re.IGNORECASE):
            return []

        try:
            pattern = re.compile(params.pattern, re.IGNORECASE)
        except re.error:
            return []

        for match in pattern.finditer(text):
            val_str = match.group(1) if match.groups() else match.group(0)
            try:
                val = float(val_str.replace(",", ""))
            except ValueError:
                continue

            tol = params.tolerance
            lim = params.limit_value
            violates = False

            if params.operator == "GE":
                violates = val < (lim - tol)
            elif params.operator == "LE":
                violates = val > (lim + tol)
            elif params.operator == "GT":
                violates = val <= lim
            elif params.operator == "LT":
                violates = val >= lim
            elif params.operator == "EQ":
                violates = abs(val - lim) > tol

            if violates:
                fact = (
                    f"{params.parameter_name} value {val} violates standard limit "
                    f"({params.operator} {lim})."
                )
                msg = rule.message_template.format(
                    parameter=params.parameter_name,
                    value=val,
                    limit=lim,
                    clause=rule.clause,
                ) if "{" in rule.message_template else rule.message_template
                rec = rule.recommendation_template.format(
                    parameter=params.parameter_name,
                    limit=lim,
                    operator=params.operator,
                    clause=rule.clause,
                ) if "{" in rule.recommendation_template else rule.recommendation_template

                findings.append(
                    self._create_finding(
                        rule=rule,
                        message=msg,
                        recommendation=rec,
                        detected_fact=fact,
                        detected_parameter=params.parameter_name,
                        detected_value=str(val),
                        page_number=page_number,
                    )
                )
        return findings

    def _eval_terminology(
        self,
        rule: ReferenceRule,
        params: TerminologyParameters,
        text: str,
        page_number: int,
    ) -> list[ReferenceFinding]:
        findings: list[ReferenceFinding] = []
        for dep in params.deprecated_terms:
            pattern = re.compile(r"\b" + re.escape(dep) + r"\b", re.IGNORECASE)
            for match in pattern.finditer(text):
                # Verify at least one keyword appears outside the deprecated term
                if params.context_keywords:
                    text_without_match = text[: match.start()] + " " + text[match.end() :]
                    found_context = any(
                        re.search(r"\b" + re.escape(kw) + r"\b", text_without_match, re.IGNORECASE)
                        for kw in params.context_keywords
                    )
                    if not found_context:
                        continue

                fact = (
                    f"Non-standard terminology '{match.group(0)}' used instead of governed "
                    f"term '{params.preferred_term}'."
                )
                msg = rule.message_template.format(
                    deprecated=match.group(0),
                    preferred=params.preferred_term,
                    clause=rule.clause,
                ) if "{" in rule.message_template else rule.message_template
                rec = rule.recommendation_template.format(
                    preferred=params.preferred_term,
                    clause=rule.clause,
                ) if "{" in rule.recommendation_template else rule.recommendation_template

                findings.append(
                    self._create_finding(
                        rule=rule,
                        message=msg,
                        recommendation=rec,
                        detected_fact=fact,
                        detected_parameter=params.term,
                        detected_value=match.group(0),
                        page_number=page_number,
                    )
                )
        return findings

    def _eval_required_reference(
        self,
        rule: ReferenceRule,
        params: RequiredReferenceParameters,
        text: str,
        page_number: int,
    ) -> list[ReferenceFinding]:
        findings: list[ReferenceFinding] = []
        triggered_keyword: str | None = None
        for kw in params.trigger_keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", text, re.IGNORECASE):
                triggered_keyword = kw
                break

        if not triggered_keyword:
            return []

        # Check for exemption keywords
        for ex in params.exemption_keywords:
            if re.search(r"\b" + re.escape(ex) + r"\b", text, re.IGNORECASE):
                return []

        # Check for presence of required standard / clause
        has_standard = bool(
            re.search(r"\b" + re.escape(params.required_standard) + r"\b", text, re.IGNORECASE)
        )
        has_clause = True
        if params.required_clause:
            has_clause = bool(
                re.search(r"\b" + re.escape(params.required_clause) + r"\b", text, re.IGNORECASE)
            )

        if not (has_standard and has_clause):
            fact = (
                f"Document specifies '{triggered_keyword}' without mandatory reference to "
                f"{params.required_standard}"
                + (f" clause {params.required_clause}" if params.required_clause else "")
                + "."
            )
            msg = rule.message_template.format(
                trigger=triggered_keyword,
                required_standard=params.required_standard,
                clause=rule.clause,
            ) if "{" in rule.message_template else rule.message_template
            rec = rule.recommendation_template.format(
                required_standard=params.required_standard,
                clause=rule.clause,
            ) if "{" in rule.recommendation_template else rule.recommendation_template

            findings.append(
                self._create_finding(
                    rule=rule,
                    message=msg,
                    recommendation=rec,
                    detected_fact=fact,
                    detected_parameter=triggered_keyword,
                    detected_value=None,
                    page_number=page_number,
                )
            )
        return findings

    @staticmethod
    def _deduplicate(findings: list[ReferenceFinding]) -> list[ReferenceFinding]:
        seen: set[tuple[str, str, int]] = set()
        unique: list[ReferenceFinding] = []
        for f in findings:
            key = (f.rule_id, f.detected_fact, f.page_number)
            if key not in seen:
                seen.add(key)
                unique.append(f)
        return unique


class RuleEvaluator:
    """Evaluates generic RuleDefinitions (SYSTEM or CUSTOM packs) against extracted facts.

    Every regex originating from a pack (system packs included, since the same
    engine serves user uploads) runs through :func:`sandboxed_search`, so a
    catastrophic pattern can only cost one timeout, never the pipeline.
    """

    def __init__(self, pack_id: str, rules: list[RuleDefinition]) -> None:
        if len(rules) > MAX_RULES_PER_RUN:
            raise ValueError(
                f"Rule set exceeds maximum of {MAX_RULES_PER_RUN} rules per run "
                f"(got {len(rules)})."
            )
        self.pack_id = pack_id
        self.rules = rules

    # ── Public API ──────────────────────────────────────────────────────

    def evaluate_rule(
        self,
        rule: RuleDefinition,
        extracted_facts: dict[str, Any],
    ) -> RuleEvaluationResult:
        """Evaluate one rule against extracted facts and return a deterministic result."""
        handler_name = _RULE_HANDLERS.get(rule.rule_type)
        base: dict[str, Any] = {
            "pack_id": self.pack_id,
            "rule_id": rule.rule_id,
            "standard_code": rule.standard_code,
            "clause": rule.clause,
            "expected_condition": rule.expected_condition,
        }
        if handler_name is None:
            return RuleEvaluationResult(
                edition=str(extracted_facts.get("edition", "")),
                source_page=1,
                detected_fact=None,
                status=RuleEvaluationStatus.UNRESOLVED,
                confidence=0.0,
                **base,
            )
        try:
            result: RuleEvaluationResult = getattr(self, handler_name)(rule, extracted_facts, base)
            return result
        except RegexTimeoutError:
            return RuleEvaluationResult(
                edition=str(extracted_facts.get("edition", "")),
                source_page=1,
                detected_fact="Evaluation timeout (possible ReDoS)",
                status=RuleEvaluationStatus.UNRESOLVED,
                confidence=0.0,
                **base,
            )

    def evaluate_facts(
        self,
        extracted_facts: dict[str, Any],
    ) -> list[RuleEvaluationResult]:
        """Evaluate the full rule set against one bundle of extracted facts."""
        return [self.evaluate_rule(rule, extracted_facts) for rule in self.rules]

    @staticmethod
    def _unresolved(
        base: dict[str, Any],
        extracted_facts: dict[str, Any],
        reason: str,
    ) -> RuleEvaluationResult:
        return RuleEvaluationResult(
            edition=str(extracted_facts.get("edition", "")),
            source_page=1,
            detected_fact=reason,
            status=RuleEvaluationStatus.UNRESOLVED,
            confidence=0.0,
            **base,
        )

    @staticmethod
    def _result(
        base: dict[str, Any],
        extracted_facts: dict[str, Any],
        source_page: int,
        status: RuleEvaluationStatus,
        detected_fact: str | None,
        confidence: float = 1.0,
        evidence_coordinates: list[BoundingBox] | None = None,
    ) -> RuleEvaluationResult:
        return RuleEvaluationResult(
            edition=str(extracted_facts.get("edition", "")),
            source_page=max(1, source_page),
            detected_fact=detected_fact,
            status=status,
            confidence=confidence,
            evidence_coordinates=evidence_coordinates
            if evidence_coordinates is not None
            else RuleEvaluator._coordinates(extracted_facts),
            **base,
        )

    # ── Shared helpers ──────────────────────────────────────────────────

    @staticmethod
    def _text(facts: dict[str, Any]) -> str:
        return str(facts.get("text", ""))

    @staticmethod
    def _page(facts: dict[str, Any]) -> int:
        return int(facts.get("page", 1))

    @staticmethod
    def _coordinates(facts: dict[str, Any]) -> list[BoundingBox]:
        coords = facts.get("coordinates", [])
        if not isinstance(coords, list):
            return []
        return [c for c in coords if isinstance(c, BoundingBox)]

    def _regex_search(
        self,
        pattern: str,
        text: str,
        flags: int = re.IGNORECASE,
    ) -> re.Match[str] | SandboxMatch | None:
        if not pattern or not text:
            return None
        try:
            compiled = re.compile(pattern, flags)
        except re.error:
            return None
        return sandboxed_search(compiled, text)

    # ── Rule Type Handlers ──────────────────────────────────────────────

    def _eval_required_citation(
        self,
        rule: RuleDefinition,
        facts: dict[str, Any],
        base: dict[str, Any],
    ) -> RuleEvaluationResult:
        p = rule.parameters
        trigger = str(p.get("trigger_keywords", ""))
        required = str(p.get("required_standard", ""))
        exemptions = p.get("exemption_keywords") or []
        text = self._text(facts)
        page = self._page(facts)

        if not self._regex_search(trigger, text):
            return self._result(base, facts, page, RuleEvaluationStatus.NOT_APPLICABLE,
                                detected_fact=None)

        for ex in exemptions:
            if self._regex_search(str(ex), text):
                return self._result(base, facts, page, RuleEvaluationStatus.PASS,
                                    detected_fact=f"Exemption present: '{ex}'",
                                    confidence=0.8)

        if self._regex_search(required, text):
            return self._result(base, facts, page, RuleEvaluationStatus.PASS,
                                detected_fact=f"Citation to {required} present.")
        return self._result(
            base, facts, page, RuleEvaluationStatus.FINDING,
            detected_fact=(
                f"Document triggers '{trigger.strip(chr(92) + 'b') or trigger}' content "
                f"without citing {required}."
            ),
        )

    def _eval_citation_edition_match(
        self,
        rule: RuleDefinition,
        facts: dict[str, Any],
        base: dict[str, Any],
    ) -> RuleEvaluationResult:
        p = rule.parameters
        citation_pattern = str(p.get("citation_pattern", ""))
        expected_edition = str(p.get("expected_edition", ""))
        text = self._text(facts)
        page = self._page(facts)

        match = self._regex_search(citation_pattern, text)
        if match is None:
            return self._result(base, facts, page, RuleEvaluationStatus.NOT_APPLICABLE,
                                detected_fact=None)
        cited_edition = (match.group(1) if match.groups() else match.group(0)).strip()
        if expected_edition and cited_edition == expected_edition:
            return self._result(base, facts, page, RuleEvaluationStatus.PASS,
                                detected_fact=f"Cited edition {cited_edition} matches.")
        return self._result(
            base, facts, page, RuleEvaluationStatus.FINDING,
            detected_fact=(
                f"Cited edition '{cited_edition}' does not match pack edition "
                f"'{expected_edition}'."
            ),
            confidence=0.9,
        )

    def _eval_required_section_field(
        self,
        rule: RuleDefinition,
        facts: dict[str, Any],
        base: dict[str, Any],
    ) -> RuleEvaluationResult:
        p = rule.parameters
        section = str(p.get("section_name", ""))
        field = str(p.get("field_name", ""))
        fields = facts.get("sections", {})
        page = self._page(facts)

        section_data = fields.get(section) if isinstance(fields, dict) else None
        if section_data is None:
            return self._result(base, facts, page, RuleEvaluationStatus.NOT_APPLICABLE,
                                detected_fact=f"Section '{section}' not found in document.")
        if isinstance(section_data, dict) and field in section_data:
            return self._result(base, facts, page, RuleEvaluationStatus.PASS,
                                detected_fact=f"Field '{field}' present in '{section}'.")
        return self._result(
            base, facts, page, RuleEvaluationStatus.FINDING,
            detected_fact=f"Required field '{field}' missing from section '{section}'.",
        )

    def _eval_numeric_range(
        self,
        rule: RuleDefinition,
        facts: dict[str, Any],
        base: dict[str, Any],
    ) -> RuleEvaluationResult:
        p = rule.parameters
        pattern = str(p.get("pattern", ""))
        min_value = p.get("min_value")
        max_value = p.get("max_value")
        inclusive_min = bool(p.get("inclusive_min", True))
        inclusive_max = bool(p.get("inclusive_max", True))
        text = self._text(facts)

        match = self._regex_search(pattern, text)
        if match is None:
            return self._result(base, facts, self._page(facts),
                                RuleEvaluationStatus.NOT_APPLICABLE, detected_fact=None)
        raw = (match.group(1) if match.groups() else match.group(0)).replace(",", "")
        try:
            value = float(raw)
        except ValueError:
            return self._unresolved(base, facts, f"Unparseable numeric value: '{raw}'")

        if min_value is not None:
            low_ok = value >= min_value if inclusive_min else value > min_value
            if not low_ok:
                return self._result(
                    base, facts, self._page(facts), RuleEvaluationStatus.FINDING,
                    detected_fact=(
                        f"Value {value} is below the minimum {min_value} "
                        f"of the permitted range."
                    ),
                )
        if max_value is not None:
            high_ok = value <= max_value if inclusive_max else value < max_value
            if not high_ok:
                return self._result(
                    base, facts, self._page(facts), RuleEvaluationStatus.FINDING,
                    detected_fact=(
                        f"Value {value} is above the maximum {max_value} "
                        f"of the permitted range."
                    ),
                )
        return self._result(base, facts, self._page(facts), RuleEvaluationStatus.PASS,
                            detected_fact=f"Value {value} within permitted range.")

    def _eval_unit_compatibility(
        self,
        rule: RuleDefinition,
        facts: dict[str, Any],
        base: dict[str, Any],
    ) -> RuleEvaluationResult:
        p = rule.parameters
        pattern = str(p.get("pattern", ""))
        allowed = {str(u).lower() for u in (p.get("allowed_units") or [])}
        forbidden = {str(u).lower() for u in (p.get("forbidden_units") or [])}
        text = self._text(facts)
        page = self._page(facts)

        match = self._regex_search(pattern, text)
        if match is None:
            return self._result(base, facts, page, RuleEvaluationStatus.NOT_APPLICABLE,
                                detected_fact=None)
        unit = (match.group(1) if match.groups() else match.group(0)).strip().lower()
        if unit in forbidden:
            return self._result(base, facts, page, RuleEvaluationStatus.FINDING,
                                detected_fact=f"Forbidden unit '{unit}' used.")
        if not allowed or unit in allowed:
            return self._result(base, facts, page, RuleEvaluationStatus.PASS,
                                detected_fact=f"Unit '{unit}' is compatible.")
        return self._result(base, facts, page, RuleEvaluationStatus.FINDING,
                            detected_fact=f"Unit '{unit}' is not in the allowed set.")

    def _eval_terminology_consistency(
        self,
        rule: RuleDefinition,
        facts: dict[str, Any],
        base: dict[str, Any],
    ) -> RuleEvaluationResult:
        p = rule.parameters
        preferred = str(p.get("preferred_term", ""))
        deprecated_terms = [str(t) for t in (p.get("deprecated_terms") or [])]
        context_keywords = [str(k) for k in (p.get("context_keywords") or [])]
        text = self._text(facts)
        page = self._page(facts)

        for dep in deprecated_terms:
            match = self._regex_search(r"(?<!\w)" + re.escape(dep) + r"(?!\w)", text)
            if match is None:
                continue
            if context_keywords:
                stripped = text[: match.start()] + " " + text[match.end() :]
                has_context = any(
                    self._regex_search(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", stripped)
                    for kw in context_keywords
                )
                if not has_context:
                    continue
            return self._result(
                base, facts, page, RuleEvaluationStatus.FINDING,
                detected_fact=(
                    f"Deprecated term '{match.group(0)}' used instead of '{preferred}'."
                ),
            )
        return self._result(base, facts, page, RuleEvaluationStatus.PASS,
                            detected_fact="No deprecated terminology found.")

    def _eval_table_prose_reconciliation(
        self,
        rule: RuleDefinition,
        facts: dict[str, Any],
        base: dict[str, Any],
    ) -> RuleEvaluationResult:
        p = rule.parameters
        tolerance = float(p.get("tolerance", 0.0))
        table_value = facts.get("table_value")
        prose_value = facts.get("prose_value")
        page = self._page(facts)

        if table_value is None or prose_value is None:
            return self._result(base, facts, page, RuleEvaluationStatus.NOT_APPLICABLE,
                                detected_fact="Table/prose pair not present in facts.")
        try:
            tv = float(table_value)
            pv = float(prose_value)
        except (TypeError, ValueError):
            return self._unresolved(base, facts, "Table/prose values are not numeric.")
        if abs(tv - pv) <= tolerance:
            return self._result(base, facts, page, RuleEvaluationStatus.PASS,
                                detected_fact=f"Table value {tv} matches prose value {pv}.")
        return self._result(
            base, facts, page, RuleEvaluationStatus.FINDING,
            detected_fact=(
                f"Table value {tv} disagrees with prose value {pv} "
                f"(tolerance {tolerance})."
            ),
        )

    def _eval_applicability_condition(
        self,
        rule: RuleDefinition,
        facts: dict[str, Any],
        base: dict[str, Any],
    ) -> RuleEvaluationResult:
        p = rule.parameters
        condition_pattern = str(p.get("condition_pattern", ""))
        text = self._text(facts)
        page = self._page(facts)

        match = self._regex_search(condition_pattern, text)
        if match is None:
            return self._result(base, facts, page, RuleEvaluationStatus.NOT_APPLICABLE,
                                detected_fact="Applicability condition not met.")
        return self._result(
            base, facts, page, RuleEvaluationStatus.UNRESOLVED,
            detected_fact=(
                f"Applicability condition '{match.group(0)}' met; "
                "requires engineering judgement."
            ),
            confidence=0.5,
        )


_RULE_HANDLERS: dict[RuleType, str] = {
    RuleType.REQUIRED_CITATION: "_eval_required_citation",
    RuleType.CITATION_EDITION_MATCH: "_eval_citation_edition_match",
    RuleType.REQUIRED_SECTION_FIELD: "_eval_required_section_field",
    RuleType.NUMERIC_RANGE: "_eval_numeric_range",
    RuleType.UNIT_COMPATIBILITY: "_eval_unit_compatibility",
    RuleType.TERMINOLOGY_CONSISTENCY: "_eval_terminology_consistency",
    RuleType.TABLE_PROSE_RECONCILIATION: "_eval_table_prose_reconciliation",
    RuleType.APPLICABILITY_CONDITION: "_eval_applicability_condition",
}

