class ArgumentValidatorConfig:
    """
    Global configuration for the argument validator decorator
    """

    _use_rich_grpc_errors = False

    @classmethod
    def set_rich_grpc_errors(cls, enabled: bool = True):
        """
        Set the option to use rich grpc errors
        """
        cls._use_rich_grpc_errors = enabled

    @classmethod
    def use_rich_grpc_errors(cls) -> bool:
        """
        Returns whether or not the option is set to use rich grpc errors
        """
        return cls._use_rich_grpc_errors
