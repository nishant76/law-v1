"""
Search API Schemas - Pydantic request/response models
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class SearchFilters(BaseModel):
    """Optional filters for search"""
    
    outcome: Optional[str] = Field(
        None,
        description="Judgment outcome filter: favour_petitioner, favour_respondent, bail_granted, bail_refused"
    )
    court: Optional[str] = Field(None, description="Court name filter (e.g. 'Punjab High Court')")
    matter_type: Optional[str] = Field(
        None,
        description="Matter type: criminal, civil, commercial, cheque_bounce, matrimonial"
    )
    year_from: Optional[int] = Field(None, ge=1950, le=2100, description="Start year")
    year_to: Optional[int] = Field(None, ge=1950, le=2100, description="End year")
    
    @validator("outcome")
    def validate_outcome(cls, v):
        if v and v not in ["favour_petitioner", "favour_respondent", "bail_granted", "bail_refused"]:
            raise ValueError(f"Invalid outcome: {v}")
        return v
    
    @validator("matter_type")
    def validate_matter_type(cls, v):
        if v and v not in ["criminal", "civil", "commercial", "cheque_bounce", "matrimonial", "property"]:
            raise ValueError(f"Invalid matter type: {v}")
        return v
    
    @validator("year_to")
    def validate_year_range(cls, v, values):
        if v and "year_from" in values and values["year_from"]:
            if v < values["year_from"]:
                raise ValueError("year_to must be >= year_from")
        return v


class SearchRequest(BaseModel):
    """Search API request"""
    
    query: str = Field(..., min_length=2, max_length=500, description="Search query")
    filters: Optional[SearchFilters] = Field(None, description="Optional filters")
    limit: int = Field(10, ge=1, le=50, description="Results per source (default 10)")


class PublicJudgmentResult(BaseModel):
    """Result from public judgment search"""
    
    case_name: str = Field(..., description="Full case name")
    petitioner: Optional[str] = Field(None, description="Petitioner/plaintiff name")
    respondent: Optional[str] = Field(None, description="Respondent/defendant name")
    court: str = Field(..., description="Court name")
    year: int = Field(..., description="Judgment year")
    judgment_date: Optional[str] = Field(None, description="ISO date string")
    citation_key: str = Field(..., description="Citation e.g. 2024 SCC 123")
    matter_type: Optional[str] = Field(None, description="Matter type")
    outcome: Optional[str] = Field(None, description="Judgment outcome")
    source_url: str = Field(..., description="URL to full text (e.g. eScR, P&H HC site)")
    official_source: str = Field(..., description="Source: escr, panhc, district_court")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Search relevance (0-1)")
    result_type: str = Field("public_judgment", description="Result source type")


class OwnFileResult(BaseModel):
    """Result from own files search"""
    
    document_id: str = Field(..., description="Document UUID")
    document_name: str = Field(..., description="Upload filename")
    page: Optional[int] = Field(None, description="Page number in document")
    excerpt: str = Field(..., description="Relevant text excerpt")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Search relevance (0-1)")
    confidence: int = Field(..., ge=0, le=10, description="AI confidence (0-10)")
    result_type: str = Field("own_file", description="Result source type")


class SearchResponse(BaseModel):
    """Search API response"""
    
    success: bool = Field(..., description="Request success status")
    query: str = Field(..., description="Original search query")
    from_your_files: List[OwnFileResult] = Field(
        default_factory=list,
        description="Results from lawyer's indexed documents"
    )
    from_public_judgments: List[PublicJudgmentResult] = Field(
        default_factory=list,
        description="Results from public judgment database"
    )
    total_results: int = Field(..., description="Total results across all sources")
    duration_ms: float = Field(..., description="Query duration in milliseconds")
    error: Optional[str] = Field(None, description="Error message if success=False")


class SynthesisOptions(BaseModel):
    """Options for answer synthesis"""
    
    use_own_files: bool = Field(True, description="Include own files in synthesis")
    use_public_judgments: bool = Field(True, description="Include public judgments in synthesis")
    include_citations: bool = Field(True, description="Extract and verify citations")


class SynthesiseRequest(BaseModel):
    """Request for RAG answer synthesis"""
    
    query: str = Field(..., min_length=2, max_length=500, description="Question to answer")
    options: Optional[SynthesisOptions] = Field(None, description="Synthesis options")


class SourceReference(BaseModel):
    """Source reference in synthesized answer"""
    
    document: str = Field(..., description="Document name or case citation")
    page: Optional[int] = Field(None, description="Page number if applicable")
    excerpt: str = Field(..., max_length=200, description="Relevant excerpt")


class SynthesisResponse(BaseModel):
    """Response from answer synthesis"""
    
    success: bool = Field(..., description="Request success")
    answer: str = Field(..., description="Synthesized answer to query")
    confidence: int = Field(..., ge=0, le=10, description="AI confidence level")
    sources: List[SourceReference] = Field(default_factory=list, description="Source references")
    answer_found: bool = Field(..., description="Whether confident answer was found")
    warning: Optional[str] = Field(
        None,
        description="Warning if confidence low (e.g. 'upload more relevant documents')"
    )
    duration_ms: float = Field(..., description="Processing duration")


# ---------------------------------------------------------------------------
# Enriched search schemas (added for unified search v2)
# ---------------------------------------------------------------------------

class CitationEnrichment(BaseModel):
    """AI-generated metadata for a single public judgment (cached in DB)."""

    facts: Optional[str] = Field(None, description="2-sentence summary of key facts")
    issue: Optional[str] = Field(None, description="Core legal question decided")
    reasoning: Optional[str] = Field(None, description="Court's key reasoning in 2 sentences")
    ratio: Optional[str] = Field(None, description="Binding legal principle established")
    relevance: Optional[str] = Field(None, description="Why this case matches the search query")


class EnrichedJudgmentResult(BaseModel):
    """Public judgment result with optional AI enrichment."""

    id: str = Field(..., description="Citation UUID")
    case_name: str = Field(..., description="Full case name")
    petitioner: Optional[str] = Field(None, description="Petitioner/plaintiff name")
    respondent: Optional[str] = Field(None, description="Respondent/defendant name")
    court: str = Field(..., description="Court name")
    year: int = Field(..., description="Judgment year")
    judgment_date: Optional[str] = Field(None, description="ISO date string")
    citation_key: str = Field(..., description="Citation e.g. 2024 SCC 123")
    matter_type: Optional[str] = Field(None, description="Matter type")
    outcome: Optional[str] = Field(None, description="Judgment outcome")
    judgment_url: Optional[str] = Field(None, description="Primary link — our self-hosted PDF copy (always works)")
    official_source_url: Optional[str] = Field(None, description="Secondary link — official government source")
    link_status: Optional[str] = Field(None, description="pending|verified|self_hosted|dead")
    source_url: Optional[str] = Field(None, description="Deprecated alias of official_source_url")
    official_source: Optional[str] = Field(None, description="Source: escr, panhc, district_court")
    summary: Optional[str] = Field(None, description="Editorial summary of the judgment")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Search relevance (0-1)")
    result_type: str = Field("public_judgment", description="Result source type")
    enrichment: Optional[CitationEnrichment] = Field(
        None,
        description="AI-generated metadata. null = background enrichment scheduled.",
    )


class SearchAnalysis(BaseModel):
    """Overall AI analysis across all public judgment results for a query."""

    trend: Optional[str] = Field(None, description="Pattern these cases show overall")
    winning_factors: List[str] = Field(default_factory=list, description="Factors that help the lawyer's position")
    risk_factors: List[str] = Field(default_factory=list, description="Factors that hurt the lawyer's position")
    strongest_case: Optional[str] = Field(None, description="Single case that best supports the query and why")
    practical_advice: Optional[str] = Field(None, description="One actionable insight for the lawyer")
    relevance_per_case: Dict[str, str] = Field(
        default_factory=dict,
        description="Per-citation relevance keyed by citation UUID — why each case helps with this specific query",
    )


class UnifiedSearchResponse(BaseModel):
    """
    Unified search response — v2.

    Extends SearchResponse with:
    - EnrichedJudgmentResult (enrichment field per result)
    - overall_analysis (SearchAnalysis | null)
    """

    success: bool = Field(..., description="Request success status")
    query: str = Field(..., description="Original search query")
    from_your_files: List[OwnFileResult] = Field(
        default_factory=list,
        description="Results from lawyer's indexed documents",
    )
    from_public_judgments: List[EnrichedJudgmentResult] = Field(
        default_factory=list,
        description="Results from public judgment database with AI enrichment",
    )
    overall_analysis: Optional[SearchAnalysis] = Field(
        None,
        description="AI analysis across all results. null when fewer than 3 public results.",
    )
    total_results: int = Field(..., description="Total results across all sources")
    duration_ms: float = Field(..., description="Query duration in milliseconds")
    error: Optional[str] = Field(None, description="Error message if success=False")
