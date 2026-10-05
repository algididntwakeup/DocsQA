"""Schemas shared by report generation and export configuration."""

from typing import Literal

from pydantic import AliasChoices, Field

from schemas.base import ApiModel


class HeaderTemplateConfig(ApiModel):
    """Configurable two-brand page header used by generated deliverables."""

    enabled: bool = Field(default=True, validation_alias=AliasChoices("enabled", "header_enabled"))
    title: str = Field(
        default="EXECUTIVE DOCUMENT REVIEW",
        max_length=180,
        validation_alias=AliasChoices("title", "title_text"),
    )
    company_logo: str | None = Field(
        default=None,
        max_length=3_000_000,
        validation_alias=AliasChoices("company_logo", "company_logo_url"),
    )
    client_logo: str | None = Field(
        default=None,
        max_length=3_000_000,
        validation_alias=AliasChoices("client_logo", "client_logo_url"),
    )
    placement: Literal["split_standard", "split_inverted", "both_left", "both_right"] = Field(
        default="split_standard",
        validation_alias=AliasChoices("placement", "logo_placement"),
    )
    show_divider: bool = Field(
        default=True,
        validation_alias=AliasChoices("show_divider", "show_border_bottom"),
    )


class ReportExportRequest(ApiModel):
    """Per-export settings; these override the saved project defaults."""

    header_config: HeaderTemplateConfig
