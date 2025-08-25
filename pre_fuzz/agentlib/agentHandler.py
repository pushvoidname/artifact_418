import os
from typing import Union, List, Dict, Optional, Literal

class UnsupportedModelError(Exception):
    """Exception raised when an unsupported model is requested."""

class APIError(Exception):
    """Exception raised for errors during API communication."""

class AgentHandler:
    """Base class for AI model handlers.
    
    Attributes:
        model_name (str): Name of the model to use
        system_prompt (Optional[str]): System prompt stored for subsequent communications
    """
    
    def __init__(self, model_name: str, api_key: Optional[str] = None, timeout: int = 120):
        """Initialize base handler.
        
        Args:
            model_name: Name of the model to use
            api_key: Optional API key (defaults to environment variable)
            timeout: API request timeout in seconds
            
        Raises:
            UnsupportedModelError: If requested model isn't supported
            ValueError: If API key is missing
        """
        self.model_name = model_name
        self.system_prompt = None
        self.timeout = timeout
        
        if not api_key:
            api_key = self._get_api_key_from_env()
            
        if not api_key:
            raise ValueError(f"API key {self.api_key_env} required for {self.__class__.__name__}")
            
        self.client = self._initialize_client(api_key)

    def _get_api_key_from_env(self) -> Optional[str]:
        """Get API key from environment variable."""
        return os.getenv(self.api_key_env)

    def set_system_prompt(self, prompt: str) -> None:
        """Set the system prompt to be used in subsequent communications.
        
        Args:
            prompt: The system prompt text to set
        """
        self.system_prompt = prompt

    def load_system_prompt_from_file(self, file_path: str) -> None:
        """Load and set system prompt from a text file.
        
        Args:
            file_path: Path to the file containing the system prompt
            
        Raises:
            FileNotFoundError: If the specified file cannot be found
            IOError: If there is an error reading the file
        """
        with open(file_path, 'r') as file:
            prompt = file.read()
        self.set_system_prompt(prompt)

    def communicate(
        self,
        messages: Union[str, List[Dict[str, str]]],
        include_system_prompt: bool = False,
        **kwargs
    ) -> str:
        """Base communication method (to be implemented by subclasses)."""
        raise NotImplementedError("Subclasses must implement this method")

class OpenAIHandler(AgentHandler):
    """Handler for OpenAI models.
    
    Supported Models:
        gpt-4o, o3-mini, o1, gpt-4.5-preview
    """
    
    SUPPORTED_MODELS = ['gpt-4o', 'o1', 'o3-mini', 'gpt-4.5-preview']
    REASONING_MODELS = ['o1', 'o3-mini']
    api_key_env = 'OPENAI_API_KEY'

    def __init__(self, model_name: str, api_key: Optional[str] = None, timeout: int = 120):
        if model_name not in self.SUPPORTED_MODELS:
            raise UnsupportedModelError(f"Unsupported OpenAI model: {model_name}")
            
        super().__init__(model_name, api_key, timeout)

    def _initialize_client(self, api_key: str):
        """Initialize OpenAI client."""
        import openai
        return openai.OpenAI(api_key=api_key, timeout=self.timeout)

    def communicate(
        self,
        messages: Union[str, List[Dict[str, str]]],
        include_system_prompt: bool = False,
        **kwargs
    ) -> str:
        """Communicate with OpenAI model.
        
        Args:
            messages: Input message(s) as string or message list
            include_system_prompt: Whether to include system prompt in messages
            **kwargs: Additional model parameters
            
        Returns:
            Model-generated response as string
            
        Raises:
            APIError: If communication fails
        """
        processed_messages = self._process_messages(messages, include_system_prompt)

        if self.model_name in self.REASONING_MODELS:
            kwargs['max_completion_tokens'] = kwargs['max_tokens']
            del kwargs['max_tokens']
            del kwargs['temperature']
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=processed_messages,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            raise APIError(f"OpenAI API request failed: {str(e)}") from e

    def _process_messages(
        self,
        messages: Union[str, List[Dict[str, str]]],
        include_system: bool
    ) -> List[Dict[str, str]]:
        """Process messages and add system prompt if required."""
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
            
        # fix system prompt to developer?
        if include_system and self.system_prompt:
            return [{"role": "developer", "content": self.system_prompt}] + messages
            
        return messages.copy()

class AnthropicHandler(AgentHandler):
    """Handler for Anthropic models.
    
    Supported Models:
        claude-3-5-haiku, claude-3-7-sonnet
    """
    
    SUPPORTED_MODELS = ['claude-3-5-haiku-20241022', 'claude-3-7-sonnet-20250219']
    api_key_env = 'ANTHROPIC_API_KEY'

    def __init__(self, model_name: str, api_key: Optional[str] = None, timeout: int = 120):
        if model_name not in self.SUPPORTED_MODELS:
            raise UnsupportedModelError(f"Unsupported Anthropic model: {model_name}")
            
        super().__init__(model_name, api_key, timeout)

    def _initialize_client(self, api_key: str):
        """Initialize Anthropic client."""
        import anthropic
        return anthropic.Anthropic(api_key=api_key, timeout=self.timeout)

    def communicate(
        self,
        messages: Union[str, List[Dict[str, str]]],
        include_system_prompt: bool = False,
        **kwargs
    ) -> str:
        """Communicate with Anthropic model.
        
        Args:
            messages: Input message(s) as string or message list
            include_system_prompt: Whether to include system prompt
            **kwargs: Additional model parameters
            
        Returns:
            Model-generated response as string
            
        Raises:
            APIError: If communication fails
        """
        processed_messages = self._process_messages(messages)
        params = self._prepare_parameters(include_system_prompt, kwargs)
        
        try:
            response = self.client.messages.create(
                model=self.model_name,
                messages=processed_messages,
                **params
            )
            return response.content[0].text
        except Exception as e:
            raise APIError(f"Anthropic API request failed: {str(e)}") from e

    def _process_messages(self, messages: Union[str, List[Dict[str, str]]]) -> List[Dict[str, str]]:
        """Convert messages to Anthropic format."""
        if isinstance(messages, str):
            return [{"role": "user", "content": messages}]
        return messages.copy()

    def _prepare_parameters(
        self,
        include_system: bool,
        kwargs: dict
    ) -> dict:
        """Prepare parameters including system prompt if needed."""
        params = kwargs.copy()
        params.setdefault('max_tokens', 8192)

        if 'stop' in params:
            del params['stop']

        if include_system and self.system_prompt:
            params['system'] = self.system_prompt
            
        return params