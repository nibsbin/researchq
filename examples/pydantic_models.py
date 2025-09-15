"""Example Pydantic models for structuring research responses"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class CybersecurityScope(str, Enum):
    """Enumeration of cybersecurity responsibility scopes"""
    INTERNAL = "internal"
    EXTERNAL = "external"
    BOTH = "both"
    NONE = "none"
    UNCLEAR = "unclear"


class ConfidenceLevel(str, Enum):
    """Confidence level for the assessment"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CybersecurityAssessment(BaseModel):
    """Structured response for cybersecurity responsibility assessments"""
    
    has_cybersecurity_responsibilities: bool = Field(
        description="Whether the department/ministry has cybersecurity responsibilities"
    )
    
    confidence: ConfidenceLevel = Field(
        description="Confidence level of the assessment"
    )
    
    scope: CybersecurityScope = Field(
        description="Whether the responsibilities are internal, external, both, or none"
    )
    
    key_responsibilities: List[str] = Field(
        default_factory=list,
        description="List of specific cybersecurity responsibilities identified"
    )
    
    handles_cyber_terrorism: Optional[bool] = Field(
        default=None,
        description="Whether the department handles cyber terrorism specifically"
    )
    
    focus_orientation: Optional[str] = Field(
        default=None,
        description="Whether the department is internally or externally focused"
    )
    
    evidence_sources: List[str] = Field(
        default_factory=list,
        description="Sources of information used for the assessment"
    )
    
    additional_notes: Optional[str] = Field(
        default=None,
        description="Any additional relevant information or caveats"
    )


class DepartmentInfo(BaseModel):
    """Structured response for general department information"""
    
    department_name: str = Field(
        description="Official name of the department/ministry"
    )
    
    country: str = Field(
        description="Country where the department is located"
    )
    
    primary_mandate: str = Field(
        description="Main purpose or mandate of the department"
    )
    
    key_functions: List[str] = Field(
        default_factory=list,
        description="List of key functions or responsibilities"
    )
    
    cybersecurity_involvement: CybersecurityAssessment = Field(
        description="Assessment of cybersecurity responsibilities"
    )
    
    website_url: Optional[str] = Field(
        default=None,
        description="Official website URL if available"
    )
    
    last_updated: Optional[str] = Field(
        default=None,
        description="When this information was last verified or updated"
    )


class SimpleYesNoResponse(BaseModel):
    """Simple yes/no response with explanation"""
    
    answer: bool = Field(
        description="Yes (true) or No (false) answer to the question"
    )
    
    confidence: ConfidenceLevel = Field(
        description="Confidence level of the answer"
    )
    
    explanation: str = Field(
        description="Brief explanation of the reasoning behind the answer"
    )
    
    sources: List[str] = Field(
        default_factory=list,
        description="Sources used to determine the answer"
    )