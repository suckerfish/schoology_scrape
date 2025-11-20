import google.generativeai as genai
from typing import Dict, Any
from absl import logging as absl_logging
from .base import NotificationProvider, NotificationMessage

# Suppress absl logging
absl_logging.set_verbosity(absl_logging.ERROR)

class GeminiProvider(NotificationProvider):
    """Gemini AI notification provider - generates AI analysis of grade changes"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.llm_model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the Gemini model"""
        if self.is_available():
            try:
                genai.configure(api_key=self.config['api_key'])
                self.llm_model = genai.GenerativeModel('gemini-2.5-flash')
            except Exception as e:
                self.logger.error(f"Failed to initialize Gemini model: {e}")
    
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
        
        if not self.llm_model:
            self._initialize_model()
            if not self.llm_model:
                self.logger.error("Failed to initialize Gemini model")
                return False
        
        try:
            # Define safety settings
            safety_settings = {
                'HARASSMENT': 'block_none',
                'SEXUALLY_EXPLICIT': 'block_none',
                'HATE_SPEECH': 'block_none'
            }
            
            # Prepare the prompt for grade analysis
            prompt = self._prepare_analysis_prompt(message)
            
            response = self.llm_model.generate_content(prompt, safety_settings=safety_settings)
            
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
        - Existing grades that changed (e.g., "Math test: 85/100 → 88/100")
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
        - "Math test grade improved: 85/100 → 88/100"
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
    
    def ask(self, question: str) -> str:
        """Direct question interface (for backward compatibility)"""
        if not self.is_available():
            return None
        
        if not self.llm_model:
            self._initialize_model()
            if not self.llm_model:
                return None
        
        try:
            safety_settings = {
                'HARASSMENT': 'block_none',
                'SEXUALLY_EXPLICIT': 'block_none',
                'HATE_SPEECH': 'block_none'
            }
            
            response = self.llm_model.generate_content(question, safety_settings=safety_settings)
            return response.text if response else None
            
        except Exception as e:
            self.logger.error(f"Failed to get Gemini response: {e}")
            return None