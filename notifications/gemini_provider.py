from google import genai
from typing import Dict, Any, Optional
from .base import NotificationProvider, NotificationMessage


class GeminiProvider(NotificationProvider):
    """Gemini AI notification provider - generates AI analysis of grade changes"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client: Optional[genai.Client] = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Gemini client"""
        if self.is_available():
            try:
                self.client = genai.Client(api_key=self.config['api_key'])
            except Exception as e:
                self.logger.error(f"Failed to initialize Gemini client: {e}")

    @property
    def provider_name(self) -> str:
        return "gemini"

    def validate_config(self) -> bool:
        """Validate Gemini configuration"""
        return 'api_key' in self.config and bool(self.config['api_key'])

    def is_available(self) -> bool:
        """Check if Gemini is available"""
        return self.validate_config()

    def send(self, message: NotificationMessage) -> bool:
        """Generate AI analysis using Gemini"""
        if not self.is_available():
            self.logger.error("Gemini provider not properly configured")
            return False

        if not self.client:
            self._initialize_client()
            if not self.client:
                self.logger.error("Failed to initialize Gemini client")
                return False

        try:
            # Prepare the prompt for grade analysis
            prompt = self._prepare_analysis_prompt(message)

            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )

            if response and response.text:
                # Store the analysis in metadata for other providers to use
                if not message.metadata:
                    message.metadata = {}
                message.metadata['ai_analysis'] = response.text

                self.logger.info("Gemini analysis generated successfully")
                return True
            else:
                self.logger.warning("Gemini returned empty response")
                return False

        except Exception as e:
            self.logger.error(f"Failed to generate Gemini analysis: {e}")
            return False

    def _prepare_analysis_prompt(self, message: NotificationMessage) -> str:
        """Prepare the analysis prompt for Gemini"""
        base_prompt = f"""
        Summarize these grade changes in natural, concise language. Include assignment names and specific grade values.

        Title: {message.title}
        Content: {message.content}

        What to report:
        - New assignments that have grades (e.g., "'Chemistry Quiz' now graded: 4.67/8")
        - Existing grades that changed (e.g., "Math test: 85/100 -> 88/100")
        - Missing/Excused/Incomplete status changes (e.g., "'Lab Report' marked as Missing")
        - Teacher comments added/changed (e.g., "Comment added: 'Great improvement!'")
        - Period/course grade changes (e.g., "Period grade now 91%")

        What NOT to report:
        - New assignments WITHOUT grades (just empty placeholders)
        - Due date changes alone
        - Changes that don't affect grades

        Examples:
        - "Chemistry Quiz now graded: 4.67/8 (58%)"
        - "Math homework graded: 10/10 (100%)"
        - "Math test grade improved: 85/100 -> 88/100"
        - "'Lab Report' marked as Missing in Science 7"

        Provide a factual summary of what grades changed or appeared.
        """

        # Add any additional context from metadata
        if message.metadata:
            if 'grade_changes' in message.metadata:
                base_prompt += f"\n\nGrade Changes Data: {message.metadata['grade_changes']}"
            if 'course_info' in message.metadata:
                base_prompt += f"\n\nCourse Information: {message.metadata['course_info']}"

        return base_prompt

    def ask(self, question: str) -> Optional[str]:
        """Direct question interface (for backward compatibility)"""
        if not self.is_available():
            return None

        if not self.client:
            self._initialize_client()
            if not self.client:
                return None

        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=question
            )
            return response.text if response else None

        except Exception as e:
            self.logger.error(f"Failed to get Gemini response: {e}")
            return None
