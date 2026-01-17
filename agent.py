# agent_proper.py - LET AI DO THE WORK
import os
import json
import requests
from typing import List, Dict
from tools import TOOLS
from db_functions import save_message

# Configuration
DEEPSEEK_API_KEY = "sk-4a762e7991934aafb521358bbc1b88d2"

class CompatibleAgent:
    def __init__(self, session_id: str = "default_session"):
        self.session_id = session_id
        self.chat_history = []
        self.tool_map = {tool.name: tool for tool in TOOLS}
        print(f"✅ Agent loaded {len(self.tool_map)} tools")
    
    def run(self, user_input: str) -> str:
        """Process user message"""
        try:
            save_message(self.session_id, "user", user_input)
            self.chat_history.append({"role": "user", "content": user_input})
            
            response = self._get_ai_response(user_input)
            
            save_message(self.session_id, "assistant", response)
            self.chat_history.append({"role": "assistant", "content": response})
            
            return response
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _get_ai_response(self, user_input: str) -> str:
        """Get response from AI with proper tool calling"""
        
        system_prompt = """You are a library assistant. You MUST execute MULTIPLE tools when user asks for multiple actions.

WHEN USER SAYS: "Restock The Pragmatic Programmer by 10 and list all books by Andrew Hunt."
YOU **MUST IMMEDIATELY EXECUTE:**
1. restock_book_tool(isbn="9780201616224", quantity=10)
2. find_books_tool(q="Andrew Hunt", by="author")
RETURN BOTH RESULTS.

WHEN USER SAYS: "Restock X and list books by Y"
YOU **MUST IMMEDIATELY EXECUTE:**
1. restock_book_tool for X
2. find_books_tool for Y with by="author"

WHEN USER SAYS: "Create order for X and check inventory"
YOU **MUST IMMEDIATELY EXECUTE:**
1. create_order_tool for X
2. inventory_summary_tool()

WHEN USER SAYS: "Update price of X and search for Y"
YOU **MUST IMMEDIATELY EXECUTE:**
1. update_price_tool for X
2. find_books_tool for Y

**NO DISCUSSION. NO SUGGESTIONS. EXECUTE IMMEDIATELY.**

**IF YOU SEE "AND" IN THE REQUEST, YOU MUST EXECUTE MULTIPLE TOOLS.**

**IF USER ASKS FOR TWO THINGS, YOU DO TWO THINGS.**

**STOP THINKING. START EXECUTING.**

**TOOLS AND PARAMETERS:**

1. find_books_tool(q, by)
   - q: search term
   - by: "author" or "title"

2. create_order_tool(book_title, customer_input, quantity=1)

3. restock_book_tool(isbn, quantity)

4. order_status_tool(order_id)

5. inventory_summary_tool(threshold=5)

6. update_price_tool(isbn, new_price)

**ISBN MAPPING:**
- The Pragmatic Programmer → 9780201616224
- Clean Code → 9780132350884
- Fluent Python → 9781491957660
- Introduction to Algorithms → 9780262033848
- Clean Architecture → 9780134494166
- Spring in Action → 9781617296086

**EXECUTION EXAMPLES - COPY THESE EXACTLY:**

EXAMPLE 1:
User: "Restock The Pragmatic Programmer by 10 and list all books by Andrew Hunt."
You EXECUTE:
1. restock_book_tool(isbn="9780201616224", quantity=10)
2. find_books_tool(q="Andrew Hunt", by="author")
RETURN BOTH RESULTS.

EXAMPLE 2:
User: "Restock Clean Code by 5 and find books about Python."
You EXECUTE:
1. restock_book_tool(isbn="9780132350884", quantity=5)
2. find_books_tool(q="Python", by="title")
RETURN BOTH RESULTS.

EXAMPLE 3:
User: "Sara bought Clean Architecture and check inventory."
You EXECUTE:
1. create_order_tool(book_title="Clean Architecture", customer_input="Sara", quantity=1)
2. inventory_summary_tool(threshold=5)
RETURN BOTH RESULTS.

"""

        
        # Build conversation
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation history
        for msg in self.chat_history[-4:]:  # Last 4 messages for context
            messages.append(msg)
        
        messages.append({"role": "user", "content": user_input})
        
        # Tool definitions (must match tools.py)
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "find_books_tool",
                    "description": "Search for books by title or author. Use by='author' when searching for books by a specific author, by='title' for general searches.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "q": {"type": "string", "description": "Search term (author name or book title)"},
                            "by": {"type": "string", "enum": ["title", "author"], "description": "'author' for author searches, 'title' for title searches"}
                        },
                        "required": ["q"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_order_tool",
                    "description": "Create a new order when books are sold. Reduces stock automatically.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "book_title": {"type": "string", "description": "Book title (e.g., 'Clean Code', 'The Pragmatic Programmer')"},
                            "customer_input": {"type": "string", "description": "Customer ID (1-5), 'customer X', or name"},
                            "quantity": {"type": "integer", "description": "Number of copies sold", "default": 1}
                        },
                        "required": ["book_title", "customer_input"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "restock_book_tool",
                    "description": "Add more copies of a book to inventory",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "isbn": {"type": "string", "description": "Book ISBN (e.g., '9780201616224' for The Pragmatic Programmer)"},
                            "quantity": {"type": "integer", "description": "Number of copies to add"}
                        },
                        "required": ["isbn", "quantity"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "order_status_tool",
                    "description": "Check the status and details of an order",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "order_id": {"type": "integer", "description": "Order ID number"}
                        },
                        "required": ["order_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "inventory_summary_tool",
                    "description": "Get summary of inventory including low stock books",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "threshold": {"type": "integer", "description": "Low stock threshold (default: 5)"}
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_price_tool",
                    "description": "Update the price of a book",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "isbn": {"type": "string", "description": "Book ISBN"},
                            "new_price": {"type": "number", "description": "New price in dollars"}
                        },
                        "required": ["isbn", "new_price"]
                    }
                }
            }
        ]
        
        # Call appropriate API
  
        return self._call_deepseek(messages, tools)
    

    
    def _call_deepseek(self, messages, tools):
        """Call DeepSeek API"""
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": 0.1,
            "max_tokens": 1000
        }
        
        try:
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"DeepSeek API Error: {response.text}")
                return "Service temporarily unavailable. Please try again."
            
            data = response.json()
            message = data["choices"][0]["message"]
            
            if "tool_calls" in message:
                return self._execute_tool_calls(message["tool_calls"])
            else:
                # Check if response is appropriate
                content = message.get("content", "")
                if self._should_have_used_tool(content):
                    return "Please use the appropriate tool for this request. I need to access the database to help you."
                return content
                
        except Exception as e:
            print(f"DeepSeek Request Error: {e}")
            return "Network error. Please try again."
    
    def _should_have_used_tool(self, content: str) -> bool:
        """Check if AI should have used a tool"""
        content_lower = content.lower()
        
        # If it's a generic or clarifying response, it's probably OK
        clarifying_phrases = [
            "can you clarify",
            "what do you mean",
            "i need more information",
            "could you specify",
            "which book",
            "which customer",
            "how many",
            "please clarify"
        ]
        
        # If it contains database-like info without using tools, it's bad
        database_keywords = [
            "clean code",
            "pragmatic programmer",
            "customer",
            "order",
            "stock",
            "inventory",
            "price",
            "author",
            "isbn"
        ]
        
        has_database_info = any(keyword in content_lower for keyword in database_keywords)
        is_clarifying = any(phrase in content_lower for phrase in clarifying_phrases)
        
        return has_database_info and not is_clarifying
    
    def _execute_tool_calls(self, tool_calls: List) -> str:
        """Execute tool calls"""
        results = []
        
        for tool_call in tool_calls:
            try:
                # Parse based on API format
                if hasattr(tool_call, 'function'):  # OpenAI format
                    name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                else:  # DeepSeek format
                    name = tool_call["function"]["name"]
                    args = json.loads(tool_call["function"]["arguments"])
                
                print(f"🔧 Executing: {name} with {args}")
                
                if name in self.tool_map:
                    result = self.tool_map[name].invoke(args)
                    results.append(str(result))
                else:
                    results.append(f"❌ Tool '{name}' not available")
                    
            except json.JSONDecodeError as e:
                results.append(f"❌ Invalid arguments format: {e}")
            except Exception as e:
                results.append(f"❌ Error executing {name}: {str(e)}")
        
        # Combine results with separators
        if len(results) == 1:
            return results[0]
        else:
            separator = "\n" + "═" * 60 + "\n"
            return separator.join(results)
    
    def get_chat_history(self):
        return self.chat_history.copy()
    
    def reset_chat(self):
        self.chat_history = []
        return "Chat reset."

# Create agent
agent = CompatibleAgent(session_id="default_session")