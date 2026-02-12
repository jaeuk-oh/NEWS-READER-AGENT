import os
import dotenv

dotenv.load_dotenv()

from crewai import Agent, Task, Crew
from crewai.project import CrewBase, agent, task, crew
from tools import web_search_tool
from services.notion import create_notion_page
from services.notifier import send_email

OUTPUT_FILE = "output/final_report.md"

@CrewBase
class News_Reader_Agent:
    agents_config = "config/agents.yaml"
    tasks_config  = "config/tasks.yaml"

    @agent
    def news_hunter_agent(self):
        return Agent(
            config=self.agents_config['news_hunter_agent'],
            tools=[web_search_tool]
        )

    @agent
    def summarizer_agent(self):
        return Agent(
            config=self.agents_config['summarizer_agent'],
            tools=[web_search_tool]
        )

    @agent
    def curator_agent(self):
        return Agent(
            config=self.agents_config['curator_agent'],
        )

    @task
    def content_harvesting_task(self):
        return Task(
            config=self.tasks_config['content_harvesting_task']
        )

    @task
    def summarization_task(self):
        return Task(
            config=self.tasks_config['summarization_task']
        )

    @task
    def final_report_assembly_task(self):
        return Task(
            config=self.tasks_config['final_report_assembly_task']
        )

    @crew
    def assemble_crew(self):
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            verbose=True,
        )


def run_crew(topic: str) -> str:
    """Run the news crew pipeline. Returns path to the generated report file."""
    News_Reader_Agent().assemble_crew().kickoff(inputs={"topic": topic})
    return OUTPUT_FILE


if __name__ == "__main__":
    topic = os.getenv("NEWS_TOPIC", "AI, AI-agent, influence of agent in industry")
    report_path = run_crew(topic)
    print(f"Report written to {report_path}")

    # Read the generated report
    with open(report_path, "r", encoding="utf-8") as f:
        report_content = f.read()

    # Translate to Korean
    try:
        from services.translator import translate_to_korean
        report_content = translate_to_korean(report_content)
        print("Report translated to Korean.")
    except Exception as e:
        print(f"Translation failed, using original English report: {e}")

    # Upload to Notion
    print("Uploading to Notion...")
    notion_url = create_notion_page(topic, report_content)
    print(f"Notion page created: {notion_url}")

    # Send email notification
    print("Sending email notification...")
    send_email(topic, report_content, notion_url)
    print("Email sent successfully!")