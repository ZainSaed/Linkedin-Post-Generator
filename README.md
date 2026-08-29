# AI LinkedIn Post Generator

An AI-powered LinkedIn content generation and publishing application built with Python, LangGraph, Google Gemini, Tavily, LangSmith, Streamlit, and the LinkedIn API.

The application turns a simple topic into a research-backed LinkedIn post, allows the user to review and edit the generated content, and uses a human-in-the-loop workflow before publishing to LinkedIn.

## Key Features

### AI-Powered LinkedIn Content Generation

Enter a topic and generate a professional, engaging LinkedIn post using Google Gemini.

The generation process is designed to produce:

- Strong opening hooks
- Natural storytelling
- Short, readable paragraphs
- Practical technical insights
- Developer-focused content
- Relevant examples
- LinkedIn-friendly formatting
- Relevant hashtags

### Web Research with Tavily

The application researches the topic before generating the post.

Tavily retrieves relevant information from the web, which is then provided to the LLM as context.

This creates a workflow where the post is generated from both the user's topic and supporting research.

### LangGraph Workflow

The backend uses LangGraph to organise the AI workflow into separate steps.

Current workflow:

START
↓
Research
↓
Generate Post
↓
END

This architecture makes the application easier to extend with additional AI nodes, tools, validation steps, and workflows.

### Human-in-the-Loop Publishing

AI-generated content is never published automatically.

After the post is generated, the user can:

1. Review the generated post
2. Edit the content
3. Approve or reject publishing

If the user rejects it, the post remains a draft.

If the user approves it, LinkedIn authentication becomes available.

This provides a clear human approval layer between AI generation and external publishing.

### LinkedIn OAuth Integration

LinkedIn authentication is separated from the content-generation workflow.

The application does not require LinkedIn authentication when generating a post.

The flow is:

Generate Post
↓
Review
↓
Human Approval
↓
Connect LinkedIn
↓
OAuth Authentication
↓
Publish

This keeps LinkedIn authentication independent from the AI workflow.

### LinkedIn Publishing

After successful authentication and final user confirmation, the application publishes the post through the LinkedIn API.

The publishing workflow includes handling for:

- Missing access tokens
- Invalid access tokens
- Expired authentication
- OAuth errors
- Permission errors
- API failures
- Publishing errors

### LangSmith Observability

LangSmith is integrated to trace the AI workflow.

This makes it possible to monitor and debug:

- Topic research
- LLM generation
- LangGraph execution
- API calls
- Errors
- Workflow performance

### Streamlit Interface

The frontend is built with Streamlit and provides a simple workflow for:

- Entering a topic
- Generating content
- Reviewing the research
- Editing the generated post
- Previewing the post
- Approving or rejecting publication
- Connecting LinkedIn
- Publishing the final post

## Architecture

The application separates the AI generation workflow from LinkedIn authentication and publishing.

User
↓
Streamlit Frontend
↓
LangGraph
↓
Tavily Research
↓
Google Gemini
↓
Generated LinkedIn Post
↓
Human Review
↓
Human Approval
↓
LinkedIn OAuth
↓
LinkedIn API
↓
Published Post

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Application development |
| Streamlit | Frontend and user interface |
| LangGraph | AI workflow orchestration |
| LangChain | LLM integration |
| Google Gemini | AI content generation |
| Tavily | Web research |
| LangSmith | Tracing and observability |
| LinkedIn API | LinkedIn authentication and publishing |
| OAuth 2.0 | Secure LinkedIn authentication |
| Requests | API communication |
| python-dotenv | Environment configuration |

## Project Structure

Linkedin-Post-Generator/
│
├── frontend.py
├── backend.py
├── requirements.txt
├── .env
├── .gitignore
└── README.md

### frontend.py

Handles the Streamlit UI, user interaction, human approval flow, LinkedIn OAuth, authentication state, and LinkedIn publishing.

### backend.py

Contains the LangGraph workflow, Tavily research, Gemini post generation, post formatting, hashtag generation, and LangSmith tracing.

## Example Workflow

The user enters:

"What I learned while building an AI agent with LangGraph"

The application then:

1. Researches the topic using Tavily
2. Passes the research to Gemini
3. Generates a LinkedIn post
4. Displays the generated content
5. Allows the user to edit the post
6. Shows a LinkedIn-style preview
7. Requests human approval
8. Provides the LinkedIn connection option
9. Authenticates through LinkedIn OAuth
10. Requests final publishing confirmation
11. Publishes the approved post

## Human-Controlled AI

A key design principle of this project is keeping the human in control of external actions.

The AI can research and generate content, but it does not independently publish content.

The final publishing process requires explicit user interaction.

AI Generation
→ Human Review
→ Human Approval
→ LinkedIn Authentication
→ Final Publish

## Local Development

Clone the repository:

git clone https://github.com/ZainSaed/Linkedin-Post-Generator.git

Create a virtual environment:

python -m venv venv

Activate it on Windows:

venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

Create a `.env` file and configure the required API credentials.

Run the application:

streamlit run frontend.py --server.port 8501

Open:

http://localhost:8501

## Environment Variables

The application uses environment variables for API credentials and configuration.

Required configuration includes:

GOOGLE_API_KEY

TAVILY_API_KEY

LINKEDIN_CLIENT_ID

LINKEDIN_CLIENT_SECRET

LINKEDIN_REDIRECT_URI

LANGSMITH_TRACING

LANGSMITH_ENDPOINT

LANGSMITH_API_KEY

LANGSMITH_PROJECT

Never commit API keys, OAuth secrets, access tokens, or `.env` files to GitHub.

## Error Handling

The application includes error handling across the main workflow.

AI and research errors are caught during generation.

LinkedIn errors are handled during authentication and publishing.

OAuth state validation is used to protect the authentication flow.

This makes failures easier to understand and prevents the application from silently continuing after an API or authentication failure.

## Future Improvements

Planned improvements could include:

- AI-generated LinkedIn images
- LinkedIn carousel generation
- Multiple writing styles
- Personal writing-style learning
- Post history
- Content scheduling
- LinkedIn analytics
- AI post scoring
- Content calendar
- Topic recommendations
- Multi-platform publishing
- Persistent database storage
- Production deployment
- Advanced LangGraph agent workflows
- RAG-based personal content generation

## What This Project Demonstrates

This project combines several concepts from modern AI application development:

- LLM application development
- Prompt engineering
- Web research
- LangChain
- LangGraph
- Human-in-the-loop workflows
- OAuth 2.0
- REST APIs
- LinkedIn API integration
- AI observability with LangSmith
- Streamlit application development
- Environment-based configuration
- External API error handling
- AI-powered automation

## Author

Zain Saed

AI Automation Developer focused on AI Agents, Generative AI, LangChain, LangGraph, MCP, n8n, Python, and business automation.

## Repository

GitHub:
https://github.com/ZainSaed/Linkedin-Post-Generator
