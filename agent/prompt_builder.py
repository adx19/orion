"""
agent/prompt_builder.py

Converts a PageContext dict into a complete, self-contained prompt for Gemini.
The prompt clearly explains the task, provides all observable page state, and
specifies exactly what JSON format Gemini must return.
"""

from __future__ import annotations

from agent.context_collector import PageContext

_SYSTEM_INSTRUCTIONS = """\
You are an autonomous browser automation agent called Orion.
Your job is to analyse the current state of a web page and decide the next action
to complete the given task.

RULES:
1. You MUST respond with valid JSON only — no markdown fences, no prose outside the JSON.
2. Choose exactly ONE of the following action types per response:

   a) Fill a form (use when the Name and Description fields are both visible):
      {
        "thought": "<brief reasoning>",
        "action": "fill_form",
        "fields": {
          "Name": "<value to type>",
          "Description": "<value to type>"
        }
      }

   b) Scroll down (use when form fields are not yet visible):
      {
        "thought": "<brief reasoning>",
        "action": "scroll",
        "direction": "down"
      }

   c) Scroll up:
      {
        "thought": "<brief reasoning>",
        "action": "scroll",
        "direction": "up"
      }

   d) Task is complete (use after the form has been filled successfully):
      {
        "thought": "<brief reasoning>",
        "action": "task_complete"
      }

   e) Click at screen coordinates (use to focus or dismiss elements):
      {
        "thought": "<brief reasoning>",
        "action": "click",
        "x": <number>,
        "y": <number>
      }

FIELD IDENTIFICATION RULES:
- A "Name" field is typically labelled: Name, Full Name, Username, Title, or similar.
- A "Description" field is typically labelled: Description, Details, Bio, Summary, or similar.
- Use the actual label text from the page — do NOT assume label names.
- If you cannot find both fields, scroll down first.

VALUE RULES:
- Choose realistic, meaningful values (not placeholder text).
- Name example: "Alex Johnson"
- Description example: "Automated form submission powered by Orion and Gemini AI"
"""


def build(ctx: PageContext) -> str:
    """
    Build a Gemini prompt from *ctx*.

    Returns the complete prompt string to send to the Gemini API.
    """
    labels_formatted = (
        "\n".join(f"  - {lbl}" for lbl in ctx["form_labels"])
        if ctx["form_labels"]
        else "  (no labels detected)"
    )

    prompt = f"""{_SYSTEM_INSTRUCTIONS}

---

CURRENT PAGE STATE:

Task         : {ctx['task']}
URL          : {ctx['url']}
Page Title   : {ctx['title']}

Visible Form Labels:
{labels_formatted}

Visible Page Text (first 4000 chars):
{ctx['text_content']}

---

Based on the page state above, what is the next action?
Respond with valid JSON only.
"""
    return prompt
