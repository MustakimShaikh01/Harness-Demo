import logging
logger=logging.getLogger("bankguard.adk")

def before_tool_callback(tool, args, tool_context):
    logger.info("tool_requested tool=%s", getattr(tool, "name", type(tool).__name__))
    return None

def after_tool_callback(tool, args, tool_context, tool_response):
    logger.info("tool_completed tool=%s", getattr(tool, "name", type(tool).__name__))
    return None
