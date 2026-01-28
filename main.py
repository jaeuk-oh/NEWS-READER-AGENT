from tabnanny import verbose
import dotenv

dotenv.load_dotenv()

from crewai import Agent, Task, Crew
from crewai.project import CrewBase, agent, task, crew
from tools import search_tool, scrape_tool

@CrewBase
class News_Reader_Agent: 

    @agent
    def news_hunter_agent(self):
        return Agent(
            config=self.agents_config['news_hunter_agent'],
            tools= [search_tool, scrape_tool]
        )
    
    @agent
    def summarizer_agent(self):
        return Agent(
            config=self.agents_config['summarizer_agent'],
            tools= [scrape_tool]
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

News_Reader_Agent().assemble_crew().kickoff(
    inputs={
        "topic": "Korea's Econimic Status"
    }
)