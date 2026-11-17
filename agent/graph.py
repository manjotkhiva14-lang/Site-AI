from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from agent.config import OUTPUT_DIR
from agent.validation import validate_business
from agent.photos import process_photos
from agent.generate_copy import generate_copy
from agent.check_copy import check_copy
from agent.build_site import build_site


class State(TypedDict, total=False):
    raw: dict
    photo_paths: list
    business: dict
    errors: list
    photos: list
    photo_problems: list
    site_data: dict
    copy_errors: list
    template_dir: str
    site_path: str


def validate(state):
    business, errors = validate_business(state["raw"])
    return {"business": business, "errors": errors}


def photos(state):
    saved, problems = process_photos(
        state.get("photo_paths", []),
        state["business"]["slug"],
        out_root=str(OUTPUT_DIR / "_photos"),
    )
    return {"photos": saved, "photo_problems": problems}


def pick_template(state):
    # One template for now. When you add more, call your pick_template here
    # and return {"template_dir": <path of the chosen template>}.
    return {}


def after_validate(state):
    return END if state["errors"] else "photos"


def make_graph():
    g = StateGraph(State)
    g.add_node("validate", validate)
    g.add_node("photos", photos)
    g.add_node("pick_template", pick_template)
    g.add_node("generate_copy", generate_copy)
    g.add_node("check_copy", check_copy)
    g.add_node("build_site", build_site)

    g.add_edge(START, "validate")
    g.add_conditional_edges("validate", after_validate)
    g.add_edge("photos", "pick_template")
    g.add_edge("pick_template", "generate_copy")
    g.add_edge("generate_copy", "check_copy")
    g.add_edge("check_copy", "build_site")
    g.add_edge("build_site", END)
    return g.compile()