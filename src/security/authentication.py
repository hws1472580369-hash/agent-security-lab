AGENTS = {
    "agent_001": {
        "role": "normal_agent",
        "api_key": "key_agent_001"
    },

    "agent_002": {
        "role": "file_agent",
        "api_key": "key_agent_002"
    },

    "admin_001": {
        "role": "admin",
        "api_key": "key_admin_001"
    }
}


def authenticate(api_key):

    for agent_id, agent in AGENTS.items():

        if agent["api_key"] == api_key:
            return agent_id

    return None