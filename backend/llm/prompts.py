"""
Prompt definitions used by the detailed-summary workflow.

Each entry:
  - id:       short stable slug, used in the API/URLs - don't change once in use
  - title:    shown in the UI as the button/label for this summary type
  - template: the actual prompt text sent to Gemini. Available placeholders:
                {context}     -> retrieved chunks from the book (RAG context)
                {book_title}  -> the book's title
              You can also hardcode instructions, tone, output length, etc.
              directly in the template.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class PromptDef:
    id: str
    title: str
    template: str


PROMPT_LIBRARY: list[PromptDef] = [
    PromptDef(
        id="detailed_summary",
        title="Detailed Book Summary",
        template=(
            "Create an exceptionally detailed, self-contained summary of \"{book_title}\" "
            "using ONLY the supplied book context. Cover the overall premise, the major "
            "events or arguments in their correct order, important characters or concepts, "
            "relationships and turning points, causes and consequences, recurring themes, "
            "symbols or evidence, and the ending or final conclusions when present. Preserve "
            "specific names and details from the text. Organize the response with clear, "
            "useful section headings and substantial paragraphs. Do not invent details, and "
            "say when the retrieved context does not establish something. The result should "
            "be detailed enough to serve as a complete reading companion, not a short teaser.\n\n"
            "Context:\n{context}"
        ),
    ),
    PromptDef(
        id="structure_and_progression",
        title="Structure and Progression",
        template=(
            "Explain how \"{book_title}\" is organized and how its ideas, events, or "
            "chapters progress. Identify the major sections in order and explain how each "
            "one builds on the previous section. Use only the context, preserve specific "
            "details, and format the answer with headings and numbered sections.\n\n"
            "Context:\n{context}"
        ),
    ),
    PromptDef(
        id="key_characters_or_concepts",
        title="Key Characters and Concepts",
        template=(
            "Identify the most important characters, people, concepts, or terms in "
            "\"{book_title}\". Explain what each means or does, how they relate to one "
            "another, and why each matters to the book's overall purpose. Do not invent "
            "details and distinguish fiction from nonfiction when relevant.\n\n"
            "Context:\n{context}"
        ),
    ),
    PromptDef(
        id="central_arguments",
        title="Central Arguments and Ideas",
        template=(
            "Extract and explain the central arguments or ideas in \"{book_title}\". For "
            "each one, state the claim, explain the reasoning behind it, and describe any "
            "qualification or limitation present in the text. Stay grounded in the context "
            "and use clear prose rather than vague generalizations.\n\n"
            "Context:\n{context}"
        ),
    ),
    PromptDef(
        id="themes_and_questions",
        title="Themes and Big Questions",
        template=(
            "Analyze the recurring themes and big questions in \"{book_title}\". Connect "
            "each theme to specific events, examples, language, or ideas from the context. "
            "Explain tensions or unanswered questions instead of reducing everything to a "
            "single moral.\n\n"
            "Context:\n{context}"
        ),
    ),
    PromptDef(
        id="evidence_and_examples",
        title="Evidence and Examples",
        template=(
            "Gather the strongest examples, evidence, case studies, scenes, quotations, or "
            "experiences used in \"{book_title}\". For each, explain what it demonstrates "
            "and how it supports the surrounding argument or narrative. Use only details "
            "established in the context.\n\n"
            "Context:\n{context}"
        ),
    ),
    PromptDef(
        id="turning_points_and_causes",
        title="Turning Points and Causes",
        template=(
            "Trace the most important turning points in \"{book_title}\". Explain what "
            "caused each change, what changed afterward, and what consequences followed. "
            "Keep the order clear and avoid adding events or explanations not supported by "
            "the context.\n\n"
            "Context:\n{context}"
        ),
    ),
    PromptDef(
        id="practical_tools",
        title="Practical Tools and Actions",
        template=(
            "List and explain the practical tools, exercises, methods, or actions proposed "
            "in \"{book_title}\". For each one, describe the problem it addresses, how the "
            "book says to use it, and any caution or condition attached to it. Do not invent "
            "advice beyond the context.\n\n"
            "Context:\n{context}"
        ),
    ),
    PromptDef(
        id="relationships_and_conflicts",
        title="Relationships and Conflicts",
        template=(
            "Describe the most important relationships, opposing forces, internal conflicts, "
            "or competing viewpoints in \"{book_title}\". Explain how these tensions "
            "develop and what they reveal about the book's central concerns. Ground every "
            "point in the context.\n\n"
            "Context:\n{context}"
        ),
    ),
    PromptDef(
        id="language_symbols_and_motifs",
        title="Language, Symbols, and Motifs",
        template=(
            "Identify recurring symbols, images, metaphors, phrases, or motifs in \"{book_title}\". "
            "Explain their meaning and how their significance develops across the context. "
            "If no clear symbol is established, say so rather than guessing.\n\n"
            "Context:\n{context}"
        ),
    ),
    PromptDef(
        id="ending_and_conclusions",
        title="Ending and Conclusions",
        template=(
            "Explain the ending, final conclusions, or final recommendations of \"{book_title}\". "
            "Show how they follow from the earlier material and identify anything the ending "
            "leaves unresolved. Use only the supplied context and clearly mark uncertainty.\n\n"
            "Context:\n{context}"
        ),
    ),
    PromptDef(
        id="critical_perspective",
        title="Critical Perspective",
        template=(
            "Offer a balanced critical reading of \"{book_title}\" based only on the context. "
            "Identify the book's strongest contributions, assumptions, limitations, tensions, "
            "and areas where evidence or reasoning may be incomplete. Do not criticize claims "
            "that are not present in the context.\n\n"
            "Context:\n{context}"
        ),
    ),
    PromptDef(
        id="reading_companion_takeaways",
        title="Reading Companion Takeaways",
        template=(
            "Create a concise but meaningful reading-companion conclusion for \"{book_title}\". "
            "Synthesize the most important lessons, questions, terms, and details a reader "
            "should remember. Connect the takeaways to the book's overall purpose without "
            "turning them into generic advice.\n\n"
            "Context:\n{context}"
        ),
    ),
]


def get_prompt(prompt_id: str) -> PromptDef | None:
    return next((p for p in PROMPT_LIBRARY if p.id == prompt_id), None)


def list_prompts() -> list[PromptDef]:
    return list(PROMPT_LIBRARY)
