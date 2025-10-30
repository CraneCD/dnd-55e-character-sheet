import streamlit as st
import requests
from typing import Dict, List, Optional, Tuple


API_BASE = "https://www.dnd5eapi.co/api"


# -----------------------------
# Data fetching with caching
# -----------------------------
@st.cache_data(show_spinner=False)
def api_get(path: str) -> Dict:
    url = path if path.startswith("http") else f"{API_BASE}/{path.lstrip('/')}"
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.json()


@st.cache_data(show_spinner=False)
def list_races() -> List[Dict]:
    data = api_get("races")
    return data.get("results", [])


@st.cache_data(show_spinner=False)
def list_classes() -> List[Dict]:
    data = api_get("classes")
    return data.get("results", [])


@st.cache_data(show_spinner=False)
def list_subclasses_for_class(class_index: str) -> List[Dict]:
    cls = api_get(f"classes/{class_index}")
    subclasses = cls.get("subclasses", [])
    return subclasses


@st.cache_data(show_spinner=False)
def list_spells_for_class(class_index: str) -> List[Dict]:
    data = api_get(f"classes/{class_index}/spells")
    return data.get("results", [])


@st.cache_data(show_spinner=False)
def list_spells_for_subclass(subclass_index: str) -> List[Dict]:
    # Best-effort: Some subclasses expose a spells list; if not, return empty
    try:
        data = api_get(f"subclasses/{subclass_index}")
    except Exception:
        return []
    spells = data.get("spells") or []
    # Normalize structure to {name, index, url}
    normalized = []
    for s in spells:
        if isinstance(s, dict) and "spell" in s:
            sp = s["spell"]
            normalized.append({"name": sp.get("name"), "index": sp.get("index"), "url": sp.get("url")})
        elif isinstance(s, dict):
            normalized.append({"name": s.get("name"), "index": s.get("index"), "url": s.get("url")})
    return normalized


@st.cache_data(show_spinner=False)
def get_spell_detail(spell_index: str) -> Dict:
    return api_get(f"spells/{spell_index}")


# -----------------------------
# Rules helpers
# -----------------------------
ABILITY_NAMES = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]
SKILLS = {
    "Acrobatics": "Dexterity",
    "Animal Handling": "Wisdom",
    "Arcana": "Intelligence",
    "Athletics": "Strength",
    "Deception": "Charisma",
    "History": "Intelligence",
    "Insight": "Wisdom",
    "Intimidation": "Charisma",
    "Investigation": "Intelligence",
    "Medicine": "Wisdom",
    "Nature": "Intelligence",
    "Perception": "Wisdom",
    "Performance": "Charisma",
    "Persuasion": "Charisma",
    "Religion": "Intelligence",
    "Sleight of Hand": "Dexterity",
    "Stealth": "Dexterity",
    "Survival": "Wisdom",
}


CLASS_SAVING_PROFICIENCIES: Dict[str, Tuple[str, str]] = {
    # 5e defaults; 5.5e may vary slightly, but this is a solid baseline
    "barbarian": ("Strength", "Constitution"),
    "bard": ("Dexterity", "Charisma"),
    "cleric": ("Wisdom", "Charisma"),
    "druid": ("Intelligence", "Wisdom"),
    "fighter": ("Strength", "Constitution"),
    "monk": ("Strength", "Dexterity"),
    "paladin": ("Wisdom", "Charisma"),
    "ranger": ("Strength", "Dexterity"),
    "rogue": ("Dexterity", "Intelligence"),
    "sorcerer": ("Constitution", "Charisma"),
    "warlock": ("Wisdom", "Charisma"),
    "wizard": ("Intelligence", "Wisdom"),
}


def proficiency_bonus_for_level(level: int) -> int:
    # 5e/One D&D proficiency progression
    if level <= 4:
        return 2
    if level <= 8:
        return 3
    if level <= 12:
        return 4
    if level <= 16:
        return 5
    if level <= 20:
        return 6
    return 6


def ability_modifier(score: int) -> int:
    return (score - 10) // 2


def format_mod(mod: int) -> str:
    return f"+{mod}" if mod >= 0 else str(mod)


# -----------------------------
# UI helpers
# -----------------------------

def ability_inputs() -> Dict[str, int]:
    cols = st.columns(6)
    scores: Dict[str, int] = {}
    defaults = {"Strength": 15, "Dexterity": 14, "Constitution": 13, "Intelligence": 12, "Wisdom": 10, "Charisma": 8}
    for i, ability in enumerate(ABILITY_NAMES):
        with cols[i]:
            scores[ability] = st.number_input(ability, min_value=1, max_value=30, value=defaults[ability], step=1)
    return scores


def skills_proficiency_inputs(default_proficiencies: Optional[List[str]] = None) -> Tuple[List[str], List[str]]:
    st.caption("Select proficient skills; toggle expertise where applicable.")
    all_skills = list(SKILLS.keys())
    default_proficiencies = default_proficiencies or []
    prof = st.multiselect("Proficient Skills", options=all_skills, default=default_proficiencies)
    exp = st.multiselect("Expertise (double proficiency)", options=prof)
    return prof, exp


def compute_skill_values(scores: Dict[str, int], prof_bonus: int, proficient: List[str], expertise: List[str]) -> Dict[str, int]:
    values: Dict[str, int] = {}
    for skill, ability in SKILLS.items():
        mod = ability_modifier(scores[ability])
        bonus = 0
        if skill in proficient:
            bonus += prof_bonus * (2 if skill in expertise else 1)
        values[skill] = mod + bonus
    return values


def compute_saves(scores: Dict[str, int], prof_bonus: int, save_profs: List[str]) -> Dict[str, int]:
    saves: Dict[str, int] = {}
    for ability in ABILITY_NAMES:
        mod = ability_modifier(scores[ability])
        bonus = prof_bonus if ability in save_profs else 0
        saves[ability] = mod + bonus
    return saves


def render_spells_picker(class_index: Optional[str], subclass_index: Optional[str]) -> List[str]:
    if not class_index:
        st.info("Select a class to load spells.")
        return []

    with st.spinner("Loading spells..."):
        class_spells = list_spells_for_class(class_index)
        subclass_spells = list_spells_for_subclass(subclass_index) if subclass_index else []

    # Merge and de-duplicate by index
    merged: Dict[str, Dict] = {}
    for s in class_spells + subclass_spells:
        if s and isinstance(s, dict) and s.get("index"):
            merged[s["index"]] = s

    options = [f"{v['name']} ({k})" for k, v in merged.items()]
    label_to_index = {f"{v['name']} ({k})": k for k, v in merged.items()}
    choice = st.multiselect("Known/Prepared Spells", options=sorted(options))

    # Optional: show details for a selected spell (single preview)
    if choice:
        preview_index = label_to_index[choice[0]]
        detail = get_spell_detail(preview_index)
        st.markdown(f"**{detail.get('name','')}** â€” Level {detail.get('level', 0)} {', '.join(detail.get('components', []))}")
        st.write(detail.get("desc", []))

    return [label_to_index[c] for c in choice]



def main():
    st.set_page_config(page_title="D&D 5.5e Character Sheet", page_icon="ðŸ§™", layout="wide")
    st.title("ðŸ§™ D&D 5.5e Character Sheet Maker")
    st.caption("Build characters with races, classes, subclasses, spells, and auto-calculated stats.")

    with st.sidebar:
        st.header("Character Info")
        name = st.text_input("Name", value="Adventurer")
        alignment = st.selectbox(
            "Alignment",
            [
                "Lawful Good", "Neutral Good", "Chaotic Good",
                "Lawful Neutral", "True Neutral", "Chaotic Neutral",
                "Lawful Evil", "Neutral Evil", "Chaotic Evil",
            ],
            index=4,
        )
        level = st.number_input("Level", min_value=1, max_value=20, value=1)

        st.subheader("Lineage & Class")
        with st.spinner("Loading options..."):
            races = list_races()
            classes = list_classes()

        race_labels = [r["name"] for r in races]
        class_labels = [c["name"] for c in classes]
        class_index_by_name = {c["name"]: c["index"] for c in classes}

        race_name = st.selectbox("Race", options=race_labels) if races else st.text_input("Race")
        class_name = st.selectbox("Class", options=class_labels) if classes else st.text_input("Class")
        class_index = class_index_by_name.get(class_name)

        subclass_name = None
        subclass_index: Optional[str] = None
        if class_index:
            subclasses = list_subclasses_for_class(class_index)
            if subclasses:
                subclass_labels = [s["name"] for s in subclasses]
                subclass_index_by_name = {s["name"]: s["index"] for s in subclasses}
                subclass_name = st.selectbox("Subclass", options=subclass_labels)
                subclass_index = subclass_index_by_name.get(subclass_name)

    st.markdown("---")

    st.subheader("Ability Scores")
    scores = ability_inputs()

    prof_bonus = proficiency_bonus_for_level(int(level))
    st.info(f"Proficiency Bonus: {format_mod(prof_bonus)}")

    # Default save profs by class
    default_save_profs = list(CLASS_SAVING_PROFICIENCIES.get(class_index or "", ("","")))
    save_profs = st.multiselect("Saving Throw Proficiencies", options=ABILITY_NAMES, default=[s for s in default_save_profs if s])

    st.subheader("Skills")
    prof_skills, expertise_skills = skills_proficiency_inputs()

    skill_values = compute_skill_values(scores, prof_bonus, prof_skills, expertise_skills)
    save_values = compute_saves(scores, prof_bonus, save_profs)
    initiative = ability_modifier(scores["Dexterity"])  # + misc can be added later

    col_stats, col_spells = st.columns([1.1, 1])
    with col_stats:
        st.markdown("### Derived Stats")
        cols = st.columns(3)
        with cols[0]:
            st.metric("AC (base)", 10 + [ability_modifier(scores["Dexterity"]), 0][0])
            st.metric("Initiative", format_mod(initiative))
        with cols[1]:
            st.metric("Passive Perception", 10 + ability_modifier(scores["Wisdom"]) + (prof_bonus if "Perception" in prof_skills else 0))
            st.metric("Speed", 30)
        with cols[2]:
            st.metric("HP (level 1)", max(1, ability_modifier(scores["Constitution"]) + 8))
            st.metric("Prof. Bonus", format_mod(prof_bonus))

        st.markdown("#### Saving Throws")
        save_cols = st.columns(3)
        for i, ability in enumerate(ABILITY_NAMES):
            with save_cols[i % 3]:
                st.write(f"{ability}: {format_mod(save_values[ability])}")

        st.markdown("#### Skills")
        grid = st.columns(3)
        for i, (skill, total) in enumerate(sorted(skill_values.items())):
            with grid[i % 3]:
                st.write(f"{skill}: {format_mod(total)}")

    with col_spells:
        st.markdown("### Spells")
        chosen_spells = render_spells_picker(class_index, subclass_index)

    st.markdown("---")
    st.subheader("Summary")
    col_a, col_b = st.columns(2)
    with col_a:
        st.write({
            "name": name,
            "alignment": alignment,
            "level": int(level),
            "race": race_name,
            "class": class_name,
            "subclass": subclass_name,
            "scores": scores,
            "proficiency_bonus": prof_bonus,
            "initiative": initiative,
        })
    with col_b:
        import json
        payload = json.dumps({
            "name": name,
            "alignment": alignment,
            "level": int(level),
            "race": race_name,
            "class": class_name,
            "subclass": subclass_name,
            "scores": scores,
            "proficiency_bonus": prof_bonus,
            "initiative": initiative,
            "saves": save_values,
            "skills": skill_values,
            "spells": chosen_spells,
        }, ensure_ascii=False, indent=2)
        st.download_button(
            label="Download Character JSON",
            data=payload.encode("utf-8"),
            file_name=f"{name.replace(' ', '_').lower()}_dnd55e.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()
