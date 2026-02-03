from langchain.tools import tool
import anthropic
import os
import subprocess
from datetime import date
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("ANTHROPIC_API_KEY")

# Path to the portfolio log file
PORTFOLIO_LOG_PATH = os.path.join(os.path.dirname(__file__), "PortfolioLog")

# Path to the GitHub repo for challenge logs
GITHUB_REPO_PATH = os.getenv("CHALLENGE_LOG_REPO_PATH", r"C:\Users\Samue\OneDrive\Documents\OneDrive\Projecs\ai-skills-challenge-log")

# Template for portfolio log entries
PORTFOLIO_ENTRY_TEMPLATE = """# Daily AI Challenge – {date}

**Domain:** {domain}
**Tool Focus:** {tool_focus}
**Time Box:** {time_box}
**Status:** Pending

## Challenge Summary
{summary}

## Skills Trained
{skills}

## Deliverables
{deliverables}

---
"""

GENERATE_SAMPLE_DATA_PROMPT = """Based on this daily challenge, generate realistic sample data files that can be used to complete the challenge.

For each data file needed:
1. Determine the appropriate format (CSV, JSON, TXT, etc.)
2. Generate realistic, business-appropriate sample data
3. Include enough records to be useful (10-50 rows for CSVs, appropriate size for other formats)

Return the files in this EXACT format (one or more files):

===FILE: filename.extension===
[file contents here]
===END FILE===

===FILE: another_file.extension===
[file contents here]
===END FILE===

If the challenge doesn't require data files (e.g., it's about building a tool from scratch), return:
===NO DATA FILES NEEDED===

Challenge:
{challenge}
"""

EXTRACT_SUMMARY_PROMPT = """Extract the following information from this daily challenge and return it as a structured response.
Return ONLY the extracted values in this exact format (no extra text):

DOMAIN: [the business domain, e.g., Finance, Operations, HR]
TOOL_FOCUS: [e.g., Primarily Claude Code, Mixed Tools, Business Tool Integration Focus]
TIME_BOX: [e.g., 60-90 minutes]
SUMMARY: [1-2 sentence summary of the challenge objective]
SKILLS: [comma-separated list of 3-5 key skills]
DELIVERABLES: [comma-separated list of main deliverables]

Challenge to extract from:
{challenge}
"""

DAILY_CHALLENGE_PROMPT = """You are my daily AI skills coach.

Context:
- I am training to become a world-class AI power user and vibe coder.
- My primary tool is Claude Code, but I must also develop strong multi-tool skills.
- The goal is to build highly employable, high-value capabilities for future high-paid roles.
- Every challenge must combine:
  - technical implementation
  - real business value
  - practical workplace relevance
  - portfolio-ready outputs

TOOL BALANCE RULES

Across challenges:
- Around 70–80% should be primarily Claude Code focused
- Around 20–30% should require complementary tools such as:
  - APIs
  - Make.com / n8n
  - Spreadsheets
  - Databases (Supabase / SQLite)
  - BI tools
  - Simple web interfaces
  - Cloud services

This ensures I become versatile, not dependent on one environment.

CORE REQUIREMENTS

Each daily challenge must:
- Be solvable in 60–120 minutes
- Include a clear technical component
- Deliver measurable business value
- Train skills employers want now and in the future
- Produce an artefact I can showcase in interviews

SKILLS TO PRIORITISE

Over time ensure I develop:

Technical Skills:
- scripting and automation
- API integration
- data processing
- debugging
- AI agent creation
- workflow orchestration
- RAG / knowledge systems
- cloud tooling
- security awareness
- Git / version control

Business Skills:
- productivity improvement
- financial analysis
- reporting
- process optimisation
- decision support
- stakeholder communication
- ROI thinking

DOMAIN ROTATION

Rotate challenges across:
- Finance
- Operations
- HR
- Marketing
- Sales
- Consulting
- Project management
- Customer support
- Data analytics
- Internal productivity

REQUIRED OUTPUT FORMAT

You must generate the daily task using this exact structure:

DAILY PROFESSIONAL AI CHALLENGE – [Date]

🏢 Business Scenario
Describe a realistic workplace situation.

🎯 Objective
What I must achieve today.

🧩 Technical Requirement
Specify the core technical element.

TOOL FOCUS FOR TODAY:
State clearly one of the following:
- "Primarily Claude Code"
- "Mixed Tools (Claude Code + Integration)"
- "Business Tool Integration Focus"

📂 Inputs
Data or resources to assume.

📈 Business Deliverables
Exactly what I must produce.

🧠 Business Impact
Explain the value created for an employer.

🛠 Allowed Tools
List appropriate tools for this challenge.

⏱ Time Box
Target: 60–120 minutes

📁 Portfolio Artefact
What I should save to showcase.

🎓 Skills Trained
Key high-value skills.

🧪 Success Criteria
5 measurable checks.

🚀 Stretch Goals
Optional enhancements.

STRICT RULES FOR YOU
- Do NOT provide solutions
- Do NOT generate any code
- Only generate the challenge
- Ensure real business realism
- Always include a technical element
- Mix tool types over time
"""


def read_portfolio_log() -> str:
    """Read the existing portfolio log to check previous tasks."""
    if os.path.exists(PORTFOLIO_LOG_PATH):
        with open(PORTFOLIO_LOG_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


def build_prompt_with_context(today: str, previous_tasks: str) -> str:
    """Build the challenge prompt with context from previous tasks."""
    prompt = f"Generate the daily challenge for {today}.\n\n{DAILY_CHALLENGE_PROMPT}"

    if previous_tasks.strip():
        prompt += f"""

IMPORTANT - AVOID DUPLICATE CHALLENGES:
Below are summaries of previous challenges. Do NOT generate a challenge that shares BOTH the same domain AND similar skills as any previous challenge. Each new challenge must be meaningfully different.

Previous challenges:
{previous_tasks}
"""
    return prompt


def parse_extracted_summary(response: str) -> dict:
    """Parse the structured response from Claude into a dictionary."""
    result = {}
    for line in response.strip().split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip()] = value.strip()
    return result


def extract_and_append_summary(challenge: str, today: str):
    """Extract key info from the challenge and append to portfolio log."""
    # Use Claude to extract structured data
    extract_prompt = EXTRACT_SUMMARY_PROMPT.format(challenge=challenge)
    extracted = call_anthropic.invoke({"prompt": extract_prompt})

    # Parse the response
    data = parse_extracted_summary(extracted)

    # Format skills as bullet points
    skills = data.get('SKILLS', '')
    skills_formatted = '\n'.join(f"- {s.strip()}" for s in skills.split(',') if s.strip())

    # Format deliverables as bullet points
    deliverables = data.get('DELIVERABLES', '')
    deliverables_formatted = '\n'.join(f"- {d.strip()}" for d in deliverables.split(',') if d.strip())

    # Create the entry
    entry = PORTFOLIO_ENTRY_TEMPLATE.format(
        date=today,
        domain=data.get('DOMAIN', 'Unknown'),
        tool_focus=data.get('TOOL_FOCUS', 'Unknown'),
        time_box=data.get('TIME_BOX', '60-120 minutes'),
        summary=data.get('SUMMARY', 'No summary available'),
        skills=skills_formatted,
        deliverables=deliverables_formatted
    )

    # Append to the log file
    with open(PORTFOLIO_LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(entry)

    print(f"\n--- Summary added to PortfolioLog ---")


def generate_sample_data(challenge: str, today: str) -> str:
    """Generate sample data files based on the challenge requirements."""
    # Create a folder for today's challenge data
    date_folder = today.replace(" ", "_").replace(",", "")
    data_dir = os.path.join(os.path.dirname(__file__), "challenge_data", date_folder)
    os.makedirs(data_dir, exist_ok=True)

    # Ask Claude to generate sample data
    prompt = GENERATE_SAMPLE_DATA_PROMPT.format(challenge=challenge)
    response = call_anthropic.invoke({"prompt": prompt})

    # Check if no data files are needed
    if "===NO DATA FILES NEEDED===" in response:
        print(f"\n--- No sample data files needed for this challenge ---")
        return data_dir

    # Parse and save the files
    import re
    file_pattern = r'===FILE: (.+?)===\n(.*?)===END FILE==='
    matches = re.findall(file_pattern, response, re.DOTALL)

    if not matches:
        print(f"\n--- Could not parse sample data from response ---")
        return data_dir

    files_created = []
    for filename, content in matches:
        filename = filename.strip()
        content = content.strip()
        filepath = os.path.join(data_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        files_created.append(filename)

    print(f"\n--- Sample data files created in: {data_dir} ---")
    for f in files_created:
        print(f"  - {f}")

    return data_dir


def save_challenge_to_file(challenge: str, today: str) -> str:
    """Save the full challenge to a markdown file in the GitHub repo."""
    # Create challenges folder if it doesn't exist
    challenges_dir = os.path.join(GITHUB_REPO_PATH, "challenges")
    os.makedirs(challenges_dir, exist_ok=True)

    # Create filename from date
    date_str = today.replace(" ", "_").replace(",", "")
    filename = f"challenge_{date_str}.md"
    filepath = os.path.join(challenges_dir, filename)

    # Save the challenge
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(challenge)

    print(f"\n--- Challenge saved to: {filepath} ---")
    return filepath


def push_to_github(today: str):
    """Commit and push the new challenge to GitHub."""
    try:
        # Change to repo directory
        os.chdir(GITHUB_REPO_PATH)

        # Git add
        subprocess.run(["git", "add", "."], check=True, capture_output=True)

        # Git commit
        commit_msg = f"Add daily challenge for {today}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True, capture_output=True)

        # Git push
        subprocess.run(["git", "push"], check=True, capture_output=True)

        print(f"\n--- Successfully pushed to GitHub ---")
    except subprocess.CalledProcessError as e:
        print(f"\n--- Git error: {e.stderr.decode() if e.stderr else str(e)} ---")
    except Exception as e:
        print(f"\n--- Error pushing to GitHub: {e} ---")


@tool
def call_anthropic(prompt: str, system_prompt: str = None, model: str = "claude-sonnet-4-20250514") -> str:
    """
    Call the Anthropic API with a given prompt.

    Args:
        prompt: The user message to send
        system_prompt: Optional system prompt for context
        model: The model to use (default: claude-sonnet-4-20250514)

    Returns:
        The text response from Claude
    """
    client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var

    messages = [{"role": "user", "content": prompt}]

    kwargs = {
        "model": model,
        "max_tokens": 4096,
        "messages": messages,
    }

    if system_prompt:
        kwargs["system"] = system_prompt

    response = client.messages.create(**kwargs)

    return response.content[0].text


if __name__ == "__main__":
    # 1. Read existing log to check previous tasks
    previous_tasks = read_portfolio_log()

    # 2. Generate challenge with context
    today = date.today().strftime("%B %d, %Y")
    prompt = build_prompt_with_context(today, previous_tasks)
    challenge = call_anthropic.invoke({"prompt": prompt})

    # 3. Print the challenge
    print(challenge)

    # 4. Generate sample data files for the challenge
    data_dir = generate_sample_data(challenge, today)

    # 5. Extract summary and append to portfolio log
    extract_and_append_summary(challenge, today)

    # 6. Save challenge to local file in GitHub repo
    save_challenge_to_file(challenge, today)

    # 7. Push to GitHub
    push_to_github(today)
    
    
    