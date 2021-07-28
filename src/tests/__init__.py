def StatusMatcher(status_code, error_message):
    class StatusMatcher:
        def __eq__(self, other):
            if other.code == status_code and other.details == error_message:
                return True
            else:
                return False

    return StatusMatcher()
