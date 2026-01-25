# Pydantic schema for novel outline
from __future__ import annotations  # add this at the very top
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class NovelMetadata(BaseModel):
    project_name: str = Field(..., description="Unique identifier for the novel project.")
    title: str
    genre: str
    sub_genres: Optional[List[str]] = None
    target_audience: Optional[str] = None
    overall_tone: Optional[str] = None
    logline: Optional[str] = None
    synopsis: Optional[str] = None
    prompt_set_directory: str = Field("prompts/default", description="Specific prompt set to use for this novel.")

class Relationship(BaseModel):
    target_character_id: str
    type_of_relationship: str
    description: str

class Character(BaseModel):
    id: str = Field(..., description="Unique ID for the character.")
    name: str
    archetype: Optional[str] = None
    physical_description: Optional[str] = None
    personality_traits: Optional[str] = None
    backstory: Optional[str] = None
    motivations: Optional[str] = None
    goals: Optional[str] = None
    flaws: Optional[str] = None
    relationships: Optional[List[Relationship]] = None
    arc_summary: Optional[str] = None

class Setting(BaseModel):
    id: str = Field(..., description="Unique ID for the setting.")
    name: str
    type: Optional[str] = None
    physical_description: Optional[str] = None
    atmosphere: Optional[str] = None
    significance_to_plot: Optional[str] = None
    key_features: Optional[List[str]] = None

class PlotPoint(BaseModel):
    id: str = Field(..., description="Unique ID for the plot point.")
    type: str = Field(..., description="Type of plot point (e.g., Inciting Incident, Climax).")
    description: str
    characters_involved: Optional[List[str]] = None # List of character IDs
    setting_id: Optional[str] = None # ID of the primary setting
    desired_outcome: Optional[str] = None
    emotional_impact: Optional[str] = None
    sub_beats: Optional[List['PlotPoint']] = None # Nested plot points

class Theme(BaseModel):
    name: str
    description: Optional[str] = None
    how_it_manifests_in_story: Optional[str] = None

class StyleGuide(BaseModel):
    writing_style: Optional[str] = None
    preferred_vocabulary: Optional[List[str]] = None
    avoid_vocabulary: Optional[List[str]] = None
    sentence_length_preference: Optional[str] = None
    pacing_preference: Optional[str] = None

class NovelOutline(BaseModel):
    metadata: NovelMetadata
    characters: List[Character] = Field(default_factory=list)
    settings: List[Setting] = Field(default_factory=list)
    plot_points: List[PlotPoint] = Field(default_factory=list)
    themes: List[Theme] = Field(default_factory=list)
    style_guide: StyleGuide = Field(default_factory=StyleGuide)

# Forward reference for recursive PlotPoint definition - removed model_rebuild() for Pydantic v2

if __name__ == '__main__':
    # Example usage
    outline_data = {
        "metadata": {
            "project_name": "the_empathy_clause",
            "title": "The Empathy Clause",
            "genre": "Sci-Fi",
            "synopsis": "In a future where emotions are suppressed, a rogue empath discovers a hidden government program and must decide whether to restore humanity's feelings, even if it means chaos.",
            "prompt_set_directory": "prompts/default"
        },
        "characters": [
            {"id": "eva", "name": "Eva Rostova", "archetype": "Hero", "physical_description": "Pale, slender, with intense blue eyes.", "personality_traits": "Quiet, observant, secretly empathetic.", "backstory": "Grew up in a emotionless society.", "motivations": "Discover truth, restore emotion.", "goals": "Uncover the program.", "flaws": "Hesitant, fears exposure.", "relationships": [{"target_character_id": "dr_kane", "type_of_relationship": "mentor", "description": "Former professor, now a contact."}]},
            {"id": "dr_kane", "name": "Dr. Elias Kane", "archetype": "Mentor", "physical_description": "Aging, kind eyes, weary.", "personality_traits": "Wise, cautious, regretful.", "backstory": "Former lead scientist on the suppression project.", "motivations": "Redeem past mistakes.", "goals": "Help Eva, prevent disaster.", "flaws": "Fearful, easily discouraged."}
        ],
        "settings": [
            {"id": "city_core", "name": "Neo-Veridia City Core", "type": "City", "physical_description": "Sleek, towering chrome buildings, automated walkways, sterile.", "atmosphere": "Orderly, quiet, oppressive.", "significance_to_plot": "Main setting for daily life and initial discoveries."},
            {"id": "underground_lab", "name": "The Archive", "type": "Secret Lab", "physical_description": "Hidden beneath the city, dimly lit, filled with old tech and data.", "atmosphere": "Mysterious, dangerous, claustrophobic.", "significance_to_plot": "Where the truth about the empathy clause is stored."}
        ],
        "plot_points": [
            {
                "id": "inciting_incident",
                "type": "Inciting Incident",
                "description": "Eva experiences a surge of suppressed emotion, triggered by a malfunctioning empathy dampener.",
                "characters_involved": ["eva"],
                "setting_id": "city_core",
                "desired_outcome": "Eva realizes she's different and seeks answers.",
                "emotional_impact": "Confusion, fear, nascent curiosity."
            },
            {
                "id": "call_to_adventure",
                "type": "Call to Adventure",
                "description": "Dr. Kane contacts Eva, revealing the 'Empathy Clause' and hinting at a solution.",
                "characters_involved": ["eva", "dr_kane"],
                "setting_id": "city_core",
                "desired_outcome": "Eva agrees to help Dr. Kane.",
                "emotional_impact": "Hope, apprehension."
            }
        ],
        "themes": [
            {"name": "The Cost of Order", "description": "Exploring the trade-off between societal control and human emotion."},
            {"name": "Reclaiming Humanity", "description": "The journey to rediscover suppressed feelings."}
        ],
        "style_guide": {
            "writing_style": "clinical, detached, with moments of raw emotional breakthrough",
            "preferred_vocabulary": ["suppression", "dampener", "protocol", "resonance", "stasis"],
            "avoid_vocabulary": ["happy", "sad", "angry"] # Initially, to emphasize emotional void
        }
    }

    try:
        outline = NovelOutline(**outline_data)
        print("NovelOutline validated successfully!")
        print(outline.model_dump_json(indent=2))
    except ValidationError as e:
        print("NovelOutline validation failed:")
        print(e.json())
