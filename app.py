import streamlit as st
import requests
import os
import json
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


@st.cache_data(show_spinner=False)
def get_race_detail(race_index: str) -> Dict:
    return api_get(f"races/{race_index}")


@st.cache_data(show_spinner=False)
def get_class_detail(class_index: str) -> Dict:
    return api_get(f"classes/{class_index}")


@st.cache_data(show_spinner=False)
def get_subclass_detail(subclass_index: str) -> Dict:
    return api_get(f"subclasses/{subclass_index}")


@st.cache_data(show_spinner=False)
def get_trait_detail(trait_index: str) -> Dict:
    return api_get(f"traits/{trait_index}")


@st.cache_data(show_spinner=False)
def list_class_features(class_index: str) -> List[Dict]:
    try:
        data = api_get(f"classes/{class_index}/features")
        return data.get("results", [])
    except Exception:
        return []


@st.cache_data(show_spinner=False)
def list_subclass_features(subclass_index: str) -> List[Dict]:
    try:
        data = api_get(f"subclasses/{subclass_index}/features")
        return data.get("results", [])
    except Exception:
        return []


@st.cache_data(show_spinner=False)
def get_feature_detail(feature_index: str) -> Dict:
    return api_get(f"features/{feature_index}")


def filter_features_up_to_level(features: List[Dict], max_level: int) -> List[Dict]:
    eligible: List[Dict] = []
    for f in features:
        try:
            idx = f.get("index")
            if not idx:
                continue
            detail = get_feature_detail(idx)
            lvl = int(detail.get("level", 0))
            if lvl <= max_level:
                # Build a short description from the first paragraph
                raw_desc = detail.get("desc", [])
                if isinstance(raw_desc, list) and raw_desc:
                    first_para = str(raw_desc[0]).strip()
                elif isinstance(raw_desc, str):
                    first_para = raw_desc.strip()
                else:
                    first_para = ""
                short_desc = (first_para[:240] + "…") if len(first_para) > 240 else first_para
                eligible.append({
                    "name": detail.get("name", f.get("name")),
                    "level": lvl,
                    "desc": short_desc,
                })
        except Exception:
            continue
    return sorted(eligible, key=lambda x: (x["level"], x["name"]))


# -----------------------------
# Local store for named characters
# -----------------------------
def _store_path() -> str:
    return os.path.join(os.getcwd(), "characters_store.json")


def load_character_store() -> Dict[str, Dict]:
    try:
        with open(_store_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def save_character_store(store: Dict[str, Dict]) -> None:
    try:
        with open(_store_path(), "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


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


# 5e armor rules reference (simplified)
# base: base AC for the armor
# dex: "full" for light, "cap2" for medium (max +2), "none" for heavy/unarmored variants that ignore Dex
ARMOR_CATALOG = [
    {"name": "None (Unarmored)", "type": "unarmored", "base": 10, "dex": "full"},
    # Light
    {"name": "Padded", "type": "light", "base": 11, "dex": "full"},
    {"name": "Leather", "type": "light", "base": 11, "dex": "full"},
    {"name": "Studded Leather", "type": "light", "base": 12, "dex": "full"},
    # Medium
    {"name": "Hide", "type": "medium", "base": 12, "dex": "cap2"},
    {"name": "Chain Shirt", "type": "medium", "base": 13, "dex": "cap2"},
    {"name": "Scale Mail", "type": "medium", "base": 14, "dex": "cap2"},
    {"name": "Breastplate", "type": "medium", "base": 14, "dex": "cap2"},
    {"name": "Half Plate", "type": "medium", "base": 15, "dex": "cap2"},
    # Heavy
    {"name": "Ring Mail", "type": "heavy", "base": 14, "dex": "none"},
    {"name": "Chain Mail", "type": "heavy", "base": 16, "dex": "none"},
    {"name": "Splint", "type": "heavy", "base": 17, "dex": "none"},
    {"name": "Plate", "type": "heavy", "base": 18, "dex": "none"},
]


def compute_ac_from_armor(scores: Dict[str, int], armor_name: str, shield: bool, misc_bonus: int) -> int:
    dex_mod = ability_modifier(scores.get("Dexterity", 10))
    # Find armor
    armor = next((a for a in ARMOR_CATALOG if a["name"] == armor_name), None)
    if armor is None:
        # Fallback: treat as unarmored
        base = 10
        dex_rule = "full"
    else:
        base = int(armor.get("base", 10))
        dex_rule = armor.get("dex", "full")
    # Dex contribution
    if dex_rule == "full":
        dex_contrib = dex_mod
    elif dex_rule == "cap2":
        dex_contrib = min(dex_mod, 2)
    else:
        dex_contrib = 0
    ac = base + max(0, dex_contrib)
    if shield:
        ac += 2
    ac += int(misc_bonus or 0)
    return int(ac)


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


@st.cache_data(show_spinner=False)
def group_spells_by_level(class_index: Optional[str], subclass_index: Optional[str]) -> Dict[int, List[Dict]]:
    if not class_index:
        return {}
    class_spells = list_spells_for_class(class_index)
    subclass_spells = list_spells_for_subclass(subclass_index) if subclass_index else []
    merged: Dict[str, Dict] = {}
    for s in class_spells + subclass_spells:
        if s and isinstance(s, dict) and s.get("index"):
            merged[s["index"]] = s
    by_level: Dict[int, List[Dict]] = {i: [] for i in range(0, 10)}
    for idx, s in merged.items():
        try:
            detail = get_spell_detail(idx)
            lvl = int(detail.get("level", 0))
            by_level.setdefault(lvl, []).append({
                "index": idx,
                "name": detail.get("name", s.get("name")),
                "level": lvl,
            })
        except Exception:
            continue
    for lvl in by_level:
        by_level[lvl] = sorted(by_level[lvl], key=lambda x: x["name"])
    return by_level


def extract_skill_name(prof_name: str) -> Optional[str]:
    # API represents as "Skill: Perception"
    if not isinstance(prof_name, str):
        return None
    if prof_name.lower().startswith("skill:"):
        return prof_name.split(":", 1)[1].strip()
    return None


@st.cache_data(show_spinner=False)
def auto_granted_skill_proficiencies(race_index: Optional[str], class_index: Optional[str], subclass_index: Optional[str]) -> List[str]:
    granted: List[str] = []
    # Race fixed proficiencies
    try:
        if race_index:
            r = get_race_detail(race_index)
            for p in r.get("starting_proficiencies", []):
                s = extract_skill_name(p.get("name"))
                if s:
                    granted.append(s)
            # Some races list traits that grant proficiencies
            for t in r.get("traits", []):
                try:
                    td = get_trait_detail(t.get("index"))
                    for p in td.get("proficiencies", []) or []:
                        s = extract_skill_name(p.get("name"))
                        if s:
                            granted.append(s)
                except Exception:
                    pass
    except Exception:
        pass
    # Subclass may grant proficiencies via features
    try:
        if subclass_index and not subclass_index.endswith("-custom"):
            feats = list_subclass_features(subclass_index)
            for f in feats:
                try:
                    fd = api_get(f"features/{f.get('index')}")
                    for p in fd.get("proficiencies", []) or []:
                        s = extract_skill_name(p.get("name"))
                        if s:
                            granted.append(s)
                except Exception:
                    pass
    except Exception:
        pass
    # Classes usually offer choices rather than fixed skill proficiencies, so we do not auto-grant from choices
    # De-duplicate
    out = sorted({g for g in granted if g in SKILLS.keys()})
    return out


def normalize_spell_state(spell_state: Optional[Dict]) -> Dict:
    normalized = {
        "slots": {lvl: 0 for lvl in range(1, 10)},
        "slots_used": {lvl: 0 for lvl in range(1, 10)},
        "prepared": {lvl: [] for lvl in range(0, 10)},
    }
    if not isinstance(spell_state, dict):
        return normalized
    # Normalize slots
    for key in ("slots", "slots_used"):
        val = spell_state.get(key, {})
        if isinstance(val, dict):
            for k, v in val.items():
                try:
                    lvl = int(k)
                except Exception:
                    continue
                if 1 <= lvl <= 9:
                    try:
                        normalized[key][lvl] = int(v)
                    except Exception:
                        pass
    # Normalize prepared
    prep = spell_state.get("prepared", {})
    if isinstance(prep, dict):
        for k, v in prep.items():
            try:
                lvl = int(k)
            except Exception:
                continue
            if 0 <= lvl <= 9:
                if isinstance(v, list):
                    normalized["prepared"][lvl] = [str(i) for i in v]
    return normalized


# -----------------------------
# UI helpers
# -----------------------------

def ability_inputs() -> Dict[str, int]:
    cols = st.columns(6)
    scores: Dict[str, int] = {}
    defaults = {"Strength": 15, "Dexterity": 14, "Constitution": 13, "Intelligence": 12, "Wisdom": 10, "Charisma": 8}
    current = st.session_state.get("scores", defaults)
    # Ensure all abilities present
    for k, v in defaults.items():
        current.setdefault(k, v)
    for i, ability in enumerate(ABILITY_NAMES):
        with cols[i]:
            scores[ability] = st.number_input(ability, min_value=1, max_value=30, value=int(current[ability]), step=1)
    st.session_state["scores"] = scores
    return scores


def skills_proficiency_inputs(default_proficiencies: Optional[List[str]] = None) -> Tuple[List[str], List[str]]:
    st.caption("Select proficient skills; toggle expertise where applicable.")
    all_skills = list(SKILLS.keys())
    default_proficiencies = st.session_state.get("prof_skills", default_proficiencies or [])
    prof = st.multiselect("Proficient Skills", options=all_skills, default=default_proficiencies)
    exp_defaults = st.session_state.get("expertise_skills", [])
    exp = st.multiselect("Expertise (double proficiency)", options=prof, default=[e for e in exp_defaults if e in prof])
    st.session_state["prof_skills"] = prof
    st.session_state["expertise_skills"] = exp
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
    st.set_page_config(page_title="D&D 5.5e Character Sheet", layout="wide")
    st.title("D&D 5.5e Character Sheet Maker")
    st.caption("Build characters with races, classes, subclasses, spells, and auto-calculated stats.")

    with st.sidebar:
        st.header("Character Info")
        name = st.text_input("Name", value=st.session_state.get("name", "Adventurer"))
        st.session_state["name"] = name
        alignment = st.selectbox(
            "Alignment",
            [
                "Lawful Good", "Neutral Good", "Chaotic Good",
                "Lawful Neutral", "True Neutral", "Chaotic Neutral",
                "Lawful Evil", "Neutral Evil", "Chaotic Evil",
            ],
            index=[
                "Lawful Good", "Neutral Good", "Chaotic Good",
                "Lawful Neutral", "True Neutral", "Chaotic Neutral",
                "Lawful Evil", "Neutral Evil", "Chaotic Evil",
            ].index(st.session_state.get("alignment", "True Neutral")),
        )
        st.session_state["alignment"] = alignment
        level = st.number_input("Level", min_value=1, max_value=20, value=int(st.session_state.get("level", 1)))
        st.session_state["level"] = int(level)

        st.subheader("Lineage & Class")
        with st.spinner("Loading options..."):
            races = list_races()
            classes = list_classes()

        race_labels = [r["name"] for r in races]
        class_labels = [c["name"] for c in classes]
        class_index_by_name = {c["name"]: c["index"] for c in classes}
        race_index_by_name = {r["name"]: r["index"] for r in races}

        if races:
            race_default = st.session_state.get("race")
            race_idx = race_labels.index(race_default) if race_default in race_labels else 0
            race_name = st.selectbox("Race", options=race_labels, index=race_idx)
        else:
            race_name = st.text_input("Race", value=st.session_state.get("race", ""))
        st.session_state["race"] = race_name
        race_index = race_index_by_name.get(race_name)

        if classes:
            class_default = st.session_state.get("class")
            class_idx = class_labels.index(class_default) if class_default in class_labels else 0
            class_name = st.selectbox("Class", options=class_labels, index=class_idx)
        else:
            class_name = st.text_input("Class", value=st.session_state.get("class", ""))
        st.session_state["class"] = class_name
        class_index = class_index_by_name.get(class_name)

        subclass_name = None
        subclass_index: Optional[str] = None
        if class_index:
            subclasses = list_subclasses_for_class(class_index)
            subclass_labels = [s["name"] for s in subclasses]
            subclass_index_by_name = {s["name"]: s["index"] for s in subclasses}
            # Add custom option for Clockwork Sorcerer
            if class_name.lower() == "sorcerer" and "Clockwork Sorcerer" not in subclass_labels:
                subclass_labels.append("Clockwork Sorcerer")
                subclass_index_by_name["Clockwork Sorcerer"] = "clockwork-sorcerer-custom"
            if subclass_labels:
                sc_default = st.session_state.get("subclass")
                sc_idx = subclass_labels.index(sc_default) if sc_default in subclass_labels else 0
                subclass_name = st.selectbox("Subclass", options=subclass_labels, index=sc_idx)
                subclass_index = subclass_index_by_name.get(subclass_name)
                st.session_state["subclass"] = subclass_name
        else:
            race_index = None

    st.markdown("---")

    tab_abilities, tab_combat, tab_spells = st.tabs(["Abilities & Skills", "Combat", "Spells"])

    with tab_abilities:
        st.subheader("Ability Scores")
        scores = ability_inputs()

        prof_bonus = proficiency_bonus_for_level(int(level))
        st.info(f"Proficiency Bonus: {format_mod(prof_bonus)}")

        default_save_profs = list(CLASS_SAVING_PROFICIENCIES.get(class_index or "", ("","")))
        save_defaults = st.session_state.get("save_profs", [s for s in default_save_profs if s])
        save_profs = st.multiselect("Saving Throw Proficiencies", options=ABILITY_NAMES, default=save_defaults)
        st.session_state["save_profs"] = save_profs

        st.subheader("Skills")
        auto_granted = auto_granted_skill_proficiencies(race_index, class_index, subclass_index)
        if auto_granted:
            st.caption("Auto-granted by ancestry/class/subclass: " + ", ".join(auto_granted))
        # Merge auto-granted with saved/current selection
        current_prof = sorted(set((st.session_state.get("prof_skills") or [])) | set(auto_granted))
        st.session_state["prof_skills"] = current_prof
        prof_skills, expertise_skills = skills_proficiency_inputs(default_proficiencies=current_prof)

        skill_values = compute_skill_values(scores, prof_bonus, prof_skills, expertise_skills)
        save_values = compute_saves(scores, prof_bonus, save_profs)
        initiative = ability_modifier(scores["Dexterity"])  # + misc can be added later

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

    with tab_combat:
        st.subheader("Combat")
        if "combat" not in st.session_state:
            st.session_state.combat = {
                "ac": 10,
                "hp_max": 10,
                "hp_current": 10,
                "hp_temp": 0,
                "death_success": 0,
                "death_failure": 0,
                "actions": "",
                "bonus_actions": "",
                "equipment": "",
            }
        ac_base = 10 + max(0, ability_modifier(scores["Dexterity"])) if 'scores' in locals() else 10
        st.session_state.combat["ac"] = st.number_input("Armor Class (AC)", min_value=0, max_value=30, value=int(st.session_state.combat.get("ac", ac_base)))

        c1, c2, c3 = st.columns(3)
        with c1:
            st.session_state.combat["hp_max"] = st.number_input("HP Max", min_value=1, max_value=999, value=int(st.session_state.combat["hp_max"]))
        with c2:
            st.session_state.combat["hp_current"] = st.number_input("HP Current", min_value=0, max_value=999, value=int(st.session_state.combat["hp_current"]))
        with c3:
            st.session_state.combat["hp_temp"] = st.number_input("Temp HP", min_value=0, max_value=999, value=int(st.session_state.combat["hp_temp"]))

        st.markdown("#### Death Saves")
        d1, d2 = st.columns(2)
        with d1:
            st.session_state.combat["death_success"] = st.number_input("Successes", min_value=0, max_value=3, value=int(st.session_state.combat["death_success"]))
        with d2:
            st.session_state.combat["death_failure"] = st.number_input("Failures", min_value=0, max_value=3, value=int(st.session_state.combat["death_failure"]))

        st.markdown("#### Actions & Equipment")
        a1, a2 = st.columns(2)
        with a1:
            st.session_state.combat["actions"] = st.text_area("Actions", value=st.session_state.combat["actions"], height=120)
            st.session_state.combat["bonus_actions"] = st.text_area("Bonus Actions", value=st.session_state.combat["bonus_actions"], height=120)
        with a2:
            st.session_state.combat["equipment"] = st.text_area("Equipment", value=st.session_state.combat["equipment"], height=252)

        st.markdown("#### Armor & Shields")
        if "armor" not in st.session_state.combat:
            st.session_state.combat["armor"] = {
                "equipped": "None (Unarmored)",
                "shield": False,
                "misc_ac_bonus": 0,
                "manual_override": False,
            }
        armor_names = [a["name"] for a in ARMOR_CATALOG]
        c_armor, c_shield = st.columns([2, 1])
        with c_armor:
            st.session_state.combat["armor"]["equipped"] = st.selectbox("Equipped Armor", options=armor_names, index=armor_names.index(st.session_state.combat["armor"]["equipped"]) if st.session_state.combat["armor"].get("equipped") in armor_names else 0)
        with c_shield:
            st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)
            st.session_state.combat["armor"]["shield"] = st.checkbox("Shield (+2 AC)", value=bool(st.session_state.combat["armor"].get("shield", False)))
        c_misc, c_override = st.columns([1, 1])
        with c_misc:
            st.session_state.combat["armor"]["misc_ac_bonus"] = st.number_input("Misc AC Bonus", min_value=-10, max_value=10, value=int(st.session_state.combat["armor"].get("misc_ac_bonus", 0)))
        with c_override:
            st.session_state.combat["armor"]["manual_override"] = st.checkbox("Manual AC Override", value=bool(st.session_state.combat["armor"].get("manual_override", False)))

        # Compute AC unless manually overridden
        if not st.session_state.combat["armor"]["manual_override"]:
            computed_ac = compute_ac_from_armor(
                scores,
                st.session_state.combat["armor"]["equipped"],
                st.session_state.combat["armor"]["shield"],
                st.session_state.combat["armor"]["misc_ac_bonus"],
            )
            st.session_state.combat["ac"] = computed_ac
        st.metric("Calculated AC", st.session_state.combat["ac"])

        st.markdown("#### Traits & Features")
        # Race traits
        try:
            if 'race_index' in locals() and race_index:
                rd = get_race_detail(race_index)
                if rd.get("traits"):
                    with st.expander(f"Race Traits — {race_name}"):
                        for t in rd["traits"]:
                            try:
                                td = get_trait_detail(t.get("index"))
                                st.markdown(f"**{td.get('name','')}**")
                                desc = td.get("desc") or []
                                if isinstance(desc, list):
                                    for p in desc[:3]:
                                        st.write(p)
                                elif isinstance(desc, str):
                                    st.write(desc)
                            except Exception:
                                st.write(t.get("name"))
        except Exception:
            pass

        # Class features (filtered by level)
        try:
            if class_index:
                feats = list_class_features(class_index)
                visible = filter_features_up_to_level(feats, int(level))
                if visible:
                    with st.expander(f"Class Features — {class_name}"):
                        for f in visible:
                            st.write(f"Level {f['level']}: {f['name']}")
                            if f.get("desc"):
                                st.caption(f["desc"])
        except Exception:
            pass

        # Subclass features (filtered by level)
        try:
            if subclass_index and not str(subclass_index).endswith("-custom"):
                sfeats = list_subclass_features(subclass_index)
                visible = filter_features_up_to_level(sfeats, int(level))
                if visible:
                    with st.expander(f"Subclass Features — {subclass_name}"):
                        for f in visible:
                            st.write(f"Level {f['level']}: {f['name']}")
                            if f.get("desc"):
                                st.caption(f["desc"])
            elif subclass_name == "Clockwork Sorcerer":
                with st.expander("Subclass Features — Clockwork Sorcerer"):
                    st.write("Restoring Balance, Bastion of Law, Trance of Order, Clockwork Cavalcade (placeholder)")
        except Exception:
            pass

    with tab_spells:
        st.subheader("Spells")
        grouped = group_spells_by_level(class_index, subclass_index)
        st.session_state.spell_state = normalize_spell_state(st.session_state.get("spell_state"))
        # Level 0 (cantrips)
        cantrips = grouped.get(0, [])
        cantrip_labels = [f"{s['name']} ({s['index']})" for s in cantrips]
        cantrip_map = {f"{s['name']} ({s['index']})": s['index'] for s in cantrips}
        prepared0 = st.session_state.spell_state.get("prepared", {}).get(0, [])
        if not isinstance(prepared0, list):
            prepared0 = []
        selected_cantrips = st.multiselect("Cantrips", options=cantrip_labels, default=[
            next((k for k in cantrip_labels if k.endswith(f"({i})")), None) for i in prepared0
        ])
        st.session_state.spell_state["prepared"][0] = [cantrip_map[lbl] for lbl in selected_cantrips if lbl]

        st.markdown("---")
        for lvl in range(1, 10):
            spells_lvl = grouped.get(lvl, [])
            with st.expander(f"Level {lvl} — {len(spells_lvl)} spells"):
                c1, c2 = st.columns(2)
                with c1:
                    st.session_state.spell_state["slots"][lvl] = st.number_input(
                        f"Level {lvl} Spell Slots", min_value=0, max_value=9,
                        value=int(st.session_state.spell_state.get("slots", {}).get(lvl, 0)), key=f"slots_{lvl}")
                with c2:
                    st.session_state.spell_state["slots_used"][lvl] = st.number_input(
                        f"Slots Expended (L{lvl})", min_value=0, max_value=9,
                        value=int(st.session_state.spell_state.get("slots_used", {}).get(lvl, 0)), key=f"slots_used_{lvl}")
                labels = [f"{s['name']} ({s['index']})" for s in spells_lvl]
                idx_map = {f"{s['name']} ({s['index']})": s['index'] for s in spells_lvl}
                prepared_lvl = st.session_state.spell_state.get("prepared", {}).get(lvl, [])
                if not isinstance(prepared_lvl, list):
                    prepared_lvl = []
                current_defaults = [next((k for k in labels if k.endswith(f"({i})")), None) for i in prepared_lvl]
                chosen = st.multiselect(f"Prepared Spells (Level {lvl})", options=labels, default=[d for d in current_defaults if d is not None], key=f"prepared_{lvl}")
                st.session_state.spell_state["prepared"][lvl] = [idx_map[c] for c in chosen]

    st.markdown("---")
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        payload = json.dumps({
            "name": name,
            "alignment": alignment,
            "level": int(level),
            "race": race_name,
            "class": class_name,
            "subclass": subclass_name,
            "scores": scores,
            "proficiency_bonus": proficiency_bonus_for_level(int(level)),
            "initiative": ability_modifier(scores["Dexterity"]),
            "save_profs": st.session_state.get("save_profs", []),
            "skills_proficiencies": st.session_state.get("prof_skills", []),
            "skills_expertise": st.session_state.get("expertise_skills", []),
            "combat": st.session_state.get("combat", {}),
            "spells": st.session_state.get("spell_state", {}),
        }, ensure_ascii=False, indent=2)
        st.download_button(
            label="Save Character",
            data=payload.encode("utf-8"),
            file_name=f"{name.replace(' ', '_').lower()}_dnd55e.json",
            mime="application/json",
        )
    with c2:
        uploaded = st.file_uploader("Load Character JSON", type=["json"])
        if uploaded:
            try:
                data = json.loads(uploaded.read())
                st.session_state["name"] = data.get("name", st.session_state.get("name", "Adventurer"))
                st.session_state["alignment"] = data.get("alignment", st.session_state.get("alignment", "True Neutral"))
                st.session_state["level"] = int(data.get("level", st.session_state.get("level", 1)))
                st.session_state["race"] = data.get("race", st.session_state.get("race", ""))
                st.session_state["class"] = data.get("class", st.session_state.get("class", ""))
                st.session_state["subclass"] = data.get("subclass", st.session_state.get("subclass", ""))
                st.session_state["scores"] = data.get("scores", st.session_state.get("scores", {}))
                st.session_state["save_profs"] = data.get("save_profs", st.session_state.get("save_profs", []))
                st.session_state["prof_skills"] = data.get("skills_proficiencies", st.session_state.get("prof_skills", []))
                st.session_state["expertise_skills"] = data.get("skills_expertise", st.session_state.get("expertise_skills", []))
                if isinstance(data.get("combat"), dict):
                    st.session_state["combat"] = data.get("combat")
                if isinstance(data.get("spells"), dict):
                    st.session_state["spell_state"] = normalize_spell_state(data.get("spells"))
                st.success("Character loaded.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to load character: {e}")
    with c3:
        st.markdown("**Save/Load by Name**")
        if st.button("Save by Name", use_container_width=True):
            store = load_character_store()
            try:
                store[name] = json.loads(payload)
                save_character_store(store)
                st.success(f"Saved '{name}'")
            except Exception as e:
                st.error(f"Failed to save: {e}")
        store = load_character_store()
        names = sorted(store.keys())
        sel_idx = names.index(name) if name in names else 0 if names else 0
        chosen_name = st.selectbox("Load by Name", options=names or [""], index=sel_idx if names else 0)
        if st.button("Load Selected", use_container_width=True, disabled=not names):
            try:
                data = store.get(chosen_name, {})
                st.session_state["name"] = data.get("name", st.session_state.get("name", "Adventurer"))
                st.session_state["alignment"] = data.get("alignment", st.session_state.get("alignment", "True Neutral"))
                st.session_state["level"] = int(data.get("level", st.session_state.get("level", 1)))
                st.session_state["race"] = data.get("race", st.session_state.get("race", ""))
                st.session_state["class"] = data.get("class", st.session_state.get("class", ""))
                st.session_state["subclass"] = data.get("subclass", st.session_state.get("subclass", ""))
                st.session_state["scores"] = data.get("scores", st.session_state.get("scores", {}))
                st.session_state["save_profs"] = data.get("save_profs", st.session_state.get("save_profs", []))
                st.session_state["prof_skills"] = data.get("skills_proficiencies", st.session_state.get("prof_skills", []))
                st.session_state["expertise_skills"] = data.get("skills_expertise", st.session_state.get("expertise_skills", []))
                if isinstance(data.get("combat"), dict):
                    st.session_state["combat"] = data.get("combat")
                if isinstance(data.get("spells"), dict):
                    st.session_state["spell_state"] = normalize_spell_state(data.get("spells"))
                st.success(f"Loaded '{chosen_name}'")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to load: {e}")


if __name__ == "__main__":
    main()
