# D&D 5.5e Character Sheet (Streamlit)

A Streamlit app to build D&D 5e/5.5e character sheets with auto-calculated stats and integrated data from the public D&D 5e API.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Features
- Races, classes, subclasses from the API
- Ability scores and auto-calculated modifiers
- Proficiency bonus by level
- Skills (proficiency + expertise) and saving throws
- Initiative, passive perception, simple baseline AC/HP/Speed
- Spells filtered by class/subclass with inline preview
- Download JSON summary

## Data Source
Public D&D 5e API: https://www.dnd5eapi.co/
