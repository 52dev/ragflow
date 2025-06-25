# This file makes Python treat the `plugin` directory as a package.

class GlobalPluginManager:
    @staticmethod
    def get_llm_tool_by_name(name: str):
        print(f"Mock GlobalPluginManager.get_llm_tool_by_name called for '{name}'")
        # Return a dummy tool object that has an invoke method
        class DummyTool:
            def get_metadata(self): # Added to support llm_tool_metadata_to_openai_tool
                return {"name": name, "description": "A dummy tool.", "parameters": {"type": "object", "properties": {}}}

            def invoke(self, **kwargs):
                print(f"Mock DummyTool {name} invoked with {kwargs}")
                return f"Dummy invocation result for {name}"

        if name.startswith("dummy_"): # Allow creating dummy tools on the fly for testing
             return DummyTool()
        return None # Or raise an error if the tool is critical

    @staticmethod
    def get_llm_tools_by_names(names: list[str]):
        print(f"Mock GlobalPluginManager.get_llm_tools_by_names called for {names}")
        tools = []
        for name in names:
            tool = GlobalPluginManager.get_llm_tool_by_name(name)
            if tool:
                tools.append(tool)
        return tools
