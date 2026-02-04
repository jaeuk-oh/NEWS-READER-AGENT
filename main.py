import os
import dotenv

dotenv.load_dotenv()

from crewai import Agent, Task, Crew
from crewai.project import CrewBase, agent, task, crew
from crewai_tools import FirecrawlSearchTool, FirecrawlScrapeWebsiteTool

search_tool = FirecrawlSearchTool()
scrape_tool = FirecrawlScrapeWebsiteTool()

OUTPUT_FILE = "output/final_report.md"


@CrewBase
class News_Reader_Agent:
    agents_config = "config/agents.yaml"
    tasks_config  = "config/tasks.yaml"

    @agent
    def news_hunter_agent(self):
        return Agent(
            config=self.agents_config['news_hunter_agent'],
            tools=[search_tool, scrape_tool]
        )

    @agent
    def summarizer_agent(self):
        return Agent(
            config=self.agents_config['summarizer_agent'],
            tools=[scrape_tool]
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