from ai_agent.tools import execute_tool


tool_name = "save_order"
arguments = {
    "customer_name": "Test Customer",
    "items": [
        {
            "product": "cookie",
            "quantity": 1,
        }
    ],
}
client_id = "+18095550000"

result = execute_tool(tool_name, arguments, client_id)
print(result)
