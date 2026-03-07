try:
    from crewai import Agent
except ImportError:
    # Fallback for testing/mock mode
    class Agent:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    class ChatOpenAI:
        def __init__(self, **kwargs):
            pass
from social_media_prompts import (
    TREND_ANALYZER_PROMPT,
    CONTENT_GENERATOR_PROMPT,
    ENGAGEMENT_RESPONDER_PROMPT,
    ANALYTICS_REPORTER_PROMPT,
    CAMPAIGN_SCHEDULER_PROMPT,
    GUARDRAILS_PROMPT,
    build_agent_prompt_with_brand
)

class AgentFactory:
    def __init__(self, brand_profile: dict):
        self.brand_profile = brand_profile
        self.llm = ChatOpenAI(model="gpt-4o") # Defaulting to gpt-4o as per prompts

    def create_trend_analyzer(self) -> Agent:
        return Agent(
            role='Trend Analyzer',
            goal='Monitor internet pulse and identify high-value trends',
            backstory=build_agent_prompt_with_brand(TREND_ANALYZER_PROMPT, self.brand_profile),
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

    def create_content_generator(self) -> Agent:
        return Agent(
            role='Content Generator',
            goal='Create platform-native, stop-the-scroll content',
            backstory=build_agent_prompt_with_brand(CONTENT_GENERATOR_PROMPT, self.brand_profile),
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

    def create_engagement_responder(self) -> Agent:
        return Agent(
            role='Engagement Responder',
            goal='Manage brand voice and community interactions',
            backstory=build_agent_prompt_with_brand(ENGAGEMENT_RESPONDER_PROMPT, self.brand_profile),
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

    def create_analytics_reporter(self) -> Agent:
        return Agent(
            role='Analytics Reporter',
            goal='Transform raw metrics into actionable narratives',
            backstory=build_agent_prompt_with_brand(ANALYTICS_REPORTER_PROMPT, self.brand_profile),
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

    def create_campaign_scheduler(self) -> Agent:
        return Agent(
            role='Campaign Scheduler',
            goal='Optimize content publishing schedules',
            backstory=build_agent_prompt_with_brand(CAMPAIGN_SCHEDULER_PROMPT, self.brand_profile),
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

    def create_guardrails_agent(self) -> Agent:
        return Agent(
            role='Brand Safety Officer',
            goal='Ensure all content is ethical and brand-safe',
            backstory=build_agent_prompt_with_brand(GUARDRAILS_PROMPT, self.brand_profile),
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
