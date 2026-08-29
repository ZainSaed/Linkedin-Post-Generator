import os
import re
import time
from typing import TypedDict

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langsmith import traceable
from tavily import TavilyClient


load_dotenv()


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY is missing.")

if not TAVILY_API_KEY:
    raise RuntimeError("TAVILY_API_KEY is missing.")


llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    google_api_key=GOOGLE_API_KEY
)


tavily = TavilyClient(
    api_key=TAVILY_API_KEY
)


class PostState(TypedDict, total=False):
    topic: str
    research: str
    post: str
    error: str


def unicode_bold(text: str) -> str:
    result = []

    for char in text:
        if "A" <= char <= "Z":
            result.append(
                chr(
                    ord(char)
                    - ord("A")
                    + 0x1D400
                )
            )

        elif "a" <= char <= "z":
            result.append(
                chr(
                    ord(char)
                    - ord("a")
                    + 0x1D41A
                )
            )

        elif "0" <= char <= "9":
            result.append(
                chr(
                    ord(char)
                    - ord("0")
                    + 0x1D7CE
                )
            )

        else:
            result.append(char)

    return "".join(result)


def clean_post(text: str) -> str:
    text = str(text or "").strip()

    text = re.sub(
        r"```(?:markdown|text)?",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = text.replace(
        "```",
        "",
    )

    text = re.sub(
        r"^\s*[-*_]{3,}\s*$",
        "",
        text,
        flags=re.MULTILINE,
    )

    text = re.sub(
        r"\*\*(.*?)\*\*",
        lambda match: unicode_bold(
            match.group(1).strip()
        ),
        text,
        flags=re.DOTALL,
    )

    text = re.sub(
        r"^\s*#{1,6}\s+",
        "",
        text,
        flags=re.MULTILINE,
    )

    text = re.sub(
        r"(?<!\*)\*([^*\n]+)\*(?!\*)",
        r"\1",
        text,
    )

    lines = []
    previous_blank = False

    for line in text.splitlines():
        line = line.rstrip()

        if not line.strip():
            if not previous_blank:
                lines.append("")

            previous_blank = True

        else:
            lines.append(line)
            previous_blank = False

    return "\n".join(lines).strip()


@traceable(
    name="LinkedIn Topic Research",
    run_type="chain",
)
def research_topic(topic: str) -> str:
    last_error = None

    for attempt in range(3):
        try:
            result = tavily.search(
                query=topic,
                search_depth="advanced",
                max_results=5,
                include_answer=True,
            )

            sections = []

            answer = result.get("answer")

            if answer:
                sections.append(
                    "Research Summary:\n"
                    + answer
                )

            for item in result.get(
                "results",
                [],
            ):
                sections.append(
                    f"Title: {item.get('title', '')}\n"
                    f"Content: {item.get('content', '')}\n"
                    f"URL: {item.get('url', '')}"
                )

            research = "\n\n".join(
                sections
            )

            if research.strip():
                return research

            raise RuntimeError(
                "No research results were returned."
            )

        except Exception as error:
            last_error = error

            if attempt < 2:
                time.sleep(
                    2 ** attempt
                )

    raise RuntimeError(
        f"Research failed: {last_error}"
    )


@traceable(
    name="Generate LinkedIn Post",
    run_type="llm",
)
def generate_linkedin_post(
    topic: str,
    research: str,
) -> str:

    prompt = f"""
You are an experienced software developer creating
high-quality LinkedIn content.

The author shares what they learn, build, test and
discover while working with AI, Generative AI, LLMs,
LangChain, LangGraph, MCP, AI agents, Python, APIs,
automation, n8n and software engineering.

TOPIC:
{topic}

RESEARCH:
{research}

Write one high-quality LinkedIn post.

STYLE:

- Human
- Natural
- Conversational
- Developer-to-developer
- First-person when appropriate
- Storytelling
- Practical
- Technically accurate
- Strong opening hook
- Short paragraphs
- Easy to scan
- Useful
- Not overly formal

The post should sound like a developer sharing
something they genuinely learned or discovered.

STRUCTURE:

1. Strong opening hook.
2. Introduce the problem, question or realisation.
3. Explain what was learned.
4. Explain the technical concept clearly.
5. Share practical lessons.
6. Explain why it matters in real projects.
7. End with a natural question.

FORMATTING:

- Short paragraphs.
- One blank line between paragraphs.
- Use bullets only when useful.
- No horizontal lines.
- Never use "---".
- No Markdown headings.
- No Markdown **bold**.
- No Markdown *italic*.
- No code blocks.
- Do not overuse emojis.
- Avoid generic motivational language.
- Avoid corporate language.

For emphasis, use Unicode bold characters.

HASHTAGS:

Generate exactly 5 relevant hashtags.

Put all 5 hashtags at the very end.

Hashtags must relate directly to the topic.

Return ONLY the final LinkedIn post.
"""

    last_error = None

    for attempt in range(3):
        try:
            response = llm.invoke(prompt)

            content = response.content

            if isinstance(content, list):
                parts = []

                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            parts.append(
                                item.get(
                                    "text",
                                    "",
                                )
                            )

                    elif isinstance(item, str):
                        parts.append(item)

                content = "\n".join(parts)

            post = clean_post(content)

            if not post:
                raise RuntimeError(
                    "The AI returned an empty post."
                )

            hashtags = re.findall(
                r"(?<!\w)#\w+",
                post,
            )

            if len(hashtags) < 5:
                post += (
                    "\n\n"
                    "#AI #GenerativeAI "
                    "#AIEngineering #LLM #Automation"
                )

            return post

        except Exception as error:
            last_error = error

            if attempt < 2:
                time.sleep(
                    2 ** attempt
                )

    raise RuntimeError(
        f"Post generation failed: {last_error}"
    )


def research_node(
    state: PostState,
):
    try:
        return {
            "research": research_topic(
                state["topic"]
            )
        }

    except Exception as error:
        return {
            "error": str(error)
        }


def generate_node(
    state: PostState,
):
    if state.get("error"):
        return state

    try:
        return {
            "post": generate_linkedin_post(
                state["topic"],
                state["research"],
            )
        }

    except Exception as error:
        return {
            "error": str(error)
        }


builder = StateGraph(
    PostState
)


builder.add_node(
    "research",
    research_node,
)


builder.add_node(
    "generate",
    generate_node,
)


builder.add_edge(
    START,
    "research",
)


builder.add_edge(
    "research",
    "generate",
)


builder.add_edge(
    "generate",
    END,
)


graph = builder.compile(
    checkpointer=InMemorySaver()
)