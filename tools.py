from langchain.tools import tool
from typing import Optional, Dict, Any
from db_functions import (
    find_books,
    create_order,
    restock_book,
    update_price,
    order_status,
    inventory_summary,
    save_tool_call,
    get_customer_id,
    get_isbn_by_title
)

# Helper functions
def get_customer_id(customer_input: str) -> Optional[int]:
    """Convert customer input to customer ID"""
    from db_functions import get_customer_id as db_get_customer_id
    return db_get_customer_id(customer_input)

def get_isbn_by_title(title: str) -> Optional[str]:
    """Get ISBN by book title"""
    from db_functions import get_isbn_by_title as db_get_isbn_by_title
    return db_get_isbn_by_title(title)

@tool
def find_books_tool(q: str, by: str = "title") -> str:
    """
    Find books by title or author.
    
    CROSS-FUNCTION RELATIONSHIPS:
    1. With create_order_tool: Check availability before creating orders
    2. With restock_book_tool: Find books that need restocking
    3. With update_price_tool: Find books before price updates
    4. With order_status_tool: Find book details for order items
    5. With inventory_summary_tool: Get details of low-stock books
    
    When used together:
    - find_books_tool + create_order_tool: Verify stock before ordering
    - find_books_tool + restock_book_tool: Identify books needing restock
    - find_books_tool + inventory_summary_tool: Detailed low-stock analysis
    
    Args:
        q: Search query
        by: Search by "title" or "author" (default: "title")
    
    Returns:
        Formatted string of matching books with current stock
    """
    result = find_books(q, by)
    
    if isinstance(result, dict) and "error" in result:
        return f"❌ Error: {result['error']}"
    
    if not result:
        return f"No books found for '{q}' (searching by {by})."
    
    # Format the results
    books_list = []
    for i, book in enumerate(result, 1):
        stock_status = "🟢 Good" if book['stock'] > 5 else "🟡 Low" if book['stock'] > 0 else "🔴 Out"
        books_list.append(
            f"{i}. **{book['title']}** by {book['author']}\n"
            f"   ISBN: {book['isbn']}, Price: ${book['price']:.2f}\n"
            f"   Stock: {book['stock']} copies ({stock_status})"
        )
    
    save_tool_call("default_session", "find_books", {"q": q, "by": by}, {"count": len(result)})
    
    return f"📚 Found {len(result)} book(s) for '{q}' (searching by {by}):\n\n" + "\n\n".join(books_list)

@tool
def create_order_tool(book_title: str, customer_input: str, quantity: int = 1) -> str:
    """
    Create a new order for a book.
    
    CROSS-FUNCTION RELATIONSHIPS:
    1. With find_books_tool: Check book existence and current stock
    2. With inventory_summary_tool: See inventory impact after order
    3. With order_status_tool: Verify the created order
    4. With restock_book_tool: Restock if needed after large order
    5. With update_price_tool: Check price before ordering
    
    When used together:
    - find_books_tool + create_order_tool: Check availability then order
    - create_order_tool + inventory_summary_tool: Order then check inventory status
    - create_order_tool + order_status_tool: Create order then verify it
    - create_order_tool + restock_book_tool: Order then restock low items
    
    Args:
        book_title: Title of the book to order
        customer_input: Customer ID or name (e.g., "1", "customer 1", "John Doe")
        quantity: Number of copies (default: 1)
    
    Returns:
        Confirmation message with order details and updated stock
    """
    # First use find_books_tool to check availability
    search_result = find_books(book_title, by="title")
    if not search_result:
        return f"❌ Book '{book_title}' not found in inventory."
    
    current_book = search_result[0]
    current_stock = current_book['stock']
    
    if current_stock < quantity:
        return f"❌ Insufficient stock for '{book_title}'. Available: {current_stock}, Requested: {quantity}"
    
    # Get customer ID
    customer_id = get_customer_id(customer_input)
    if not customer_id:
        return f"Customer '{customer_input}' not found. Please use customer ID 1-5."
    
    # Get ISBN
    isbn = get_isbn_by_title(book_title)
    if not isbn:
        return f"Could not find ISBN for book '{book_title}'."
    
    # Create order
    result = create_order(customer_id, [{"isbn": isbn, "qty": quantity}])
    
    if "error" in result:
        return f"Error creating order: {result['error']}"
    
    # Log tool call
    save_tool_call("default_session", "create_order", 
                  {"book_title": book_title, "customer_input": customer_input, "quantity": quantity},
                  {"order_id": result['order_id'], "total_amount": result['total_amount']})
    
    response = f"✅ **Order #{result['order_id']} Created Successfully!**\n\n"
    response += f"Order Details:\n"
    response += f"  • Order ID: {result['order_id']}\n"
    response += f"  • Customer: ID {customer_id}\n"
    response += f"  • Book: {book_title}\n"
    response += f"  • Quantity: {quantity}\n"
    response += f"  • Total: ${result['total_amount']:.2f}\n"
    response += f"  • Status: {result['status']}\n\n"
    
    # Show stock change
    if "stock_changes" in result and result["stock_changes"]:
        for change in result["stock_changes"]:
            response += f"📊 Stock Update:\n"
            response += f"  • Book: {change['title']}\n"
            response += f"  • Old stock: {change['old_stock']} copies\n"
            response += f"  • New stock: {change['new_stock']} copies\n"
            response += f"  • Reduction: {change['old_stock'] - change['new_stock']} copies\n"
    
    # Suggest related actions
    response += f"\nRelated Actions:\n"
    response += f"  • Check order: `order_status_tool(order_id={result['order_id']})`\n"
    response += f"  • View inventory: `inventory_summary_tool(threshold=5)`\n"
    if result.get('stock_changes', [{}])[0].get('new_stock', 0) < 3:
        response += f"  ⚠️ Low stock! Consider: `restock_book_tool(isbn='{isbn}', quantity=10)`\n"
    
    return response

@tool
def restock_book_tool(isbn: str, quantity: int) -> str:
    """
    Restock a book by adding more copies.
    
    CROSS-FUNCTION RELATIONSHIPS:
    1. With find_books_tool: Find books needing restock
    2. With inventory_summary_tool: Check overall inventory before/after
    3. With create_order_tool: Restock after large orders
    4. With order_status_tool: Restock books from recent orders
    5. With update_price_tool: Update price during restock
    
    When used together:
    - inventory_summary_tool + restock_book_tool: Identify then restock low items
    - find_books_tool + restock_book_tool: Find book then restock it
    - create_order_tool + restock_book_tool: Order then restock same book
    - order_status_tool + restock_book_tool: Check orders then restock popular items
    
    Args:
        isbn: Book ISBN (e.g., "9780201616224")
        quantity: Number of copies to add
    
    Returns:
        Confirmation message with updated stock
    """
    # Check current stock using find_books
    all_books = find_books("", by="title")
    current_book = None
    for book in all_books:
        if book['isbn'] == isbn:
            current_book = book
            break
    
    if not current_book:
        return f"❌ Book with ISBN {isbn} not found."
    
    old_stock = current_book['stock']
    
    # Restock the book
    result = restock_book(isbn, quantity)
    
    if "error" in result:
        return f"Error: {result['error']}"
    
    # Log tool call
    save_tool_call("default_session", "restock_book", 
                  {"isbn": isbn, "quantity": quantity},
                  {"title": result['title'], "old_stock": old_stock, "new_stock": result['new_stock']})
    
    response = f"**Successfully Restocked!**\n\n"
    response += f"Restock Details:\n"
    response += f"  • Book: {result['title']}\n"
    response += f"  • ISBN: {isbn}\n"
    response += f"  • Added: {quantity} copies\n"
    response += f"  • Old stock: {old_stock} copies\n"
    response += f"  • New stock: {result['new_stock']} copies\n"
    response += f"  • Increase: {quantity} copies (+{quantity/old_stock*100:.1f}%)\n\n"
    
    # Check inventory impact
    inventory = inventory_summary(5)
    low_stock_count = inventory.get('low_stock_count', 0)
    
    response += f"📊 Inventory Impact:\n"
    response += f"  • Total inventory value: ${inventory.get('total_inventory_value', 0):.2f}\n"
    response += f"  • Low stock items: {low_stock_count}\n"
    return response
@tool
def update_price_tool(isbn: str, new_price: float) -> str:
    """
    Update the price of a book.
    
    CROSS-FUNCTION RELATIONSHIPS:
    1. With find_books_tool: Find book before price change
    2. With create_order_tool: Update price then create order
    3. With inventory_summary_tool: See price impact on inventory value
    4. With restock_book_tool: Update price during restock
    5. With order_status_tool: Check orders with old vs new prices
    
    When used together:
    - find_books_tool + update_price_tool: Find book then update its price
    - update_price_tool + create_order_tool: Update price then create order
    - update_price_tool + inventory_summary_tool: Update price then check inventory value
    - restock_book_tool + update_price_tool: Restock then update price
    
    Args:
        isbn: Book ISBN
        new_price: New price in dollars
    
    Returns:
        Confirmation message with price change
    """
    # Find current book details
    all_books = find_books("", by="title")
    current_book = None
    for book in all_books:
        if book['isbn'] == isbn:
            current_book = book
            break
    
    if not current_book:
        return f"Book with ISBN {isbn} not found."
    
    old_price = current_book['price']
    
    # Update price
    result = update_price(isbn, new_price)
    
    if "error" in result:
        return f"❌ Error: {result['error']}"
    
    # Calculate changes
    price_change = new_price - old_price
    percent_change = (price_change / old_price * 100) if old_price > 0 else 0
    inventory_value_change = price_change * current_book['stock']
    
    # Log tool call
    save_tool_call("default_session", "update_price", 
                  {"isbn": isbn, "new_price": new_price},
                  {"title": result['title'], "old_price": old_price, "new_price": new_price})
    
    response = f"**Price Updated Successfully!**\n\n"
    response += f"Price Change Details:\n"
    response += f"  • Book: {result['title']}\n"
    response += f"  • ISBN: {isbn}\n"
    response += f"  • Old price: ${old_price:.2f}\n"
    response += f"  • New price: ${new_price:.2f}\n"
    response += f"  • Change: ${price_change:+.2f} ({percent_change:+.1f}%)\n"
    response += f"  • Current stock: {current_book['stock']} copies\n"
    response += f"  • Inventory value change: ${inventory_value_change:+.2f}\n\n"
    
    # Check inventory summary
    inventory = inventory_summary(5)
    
    response += f"📊 Inventory Impact:\n"
    response += f"  • New total inventory value: ${inventory.get('total_inventory_value', 0):.2f}\n"
    response += f"  • Book's new total value: ${new_price * current_book['stock']:.2f}\n\n"
    
    # Suggest related actions
    response += f"Related Actions:\n"
    if price_change > 0:
        response += f"  • Consider restock discount: `restock_book_tool(isbn='{isbn}', quantity=10)`\n"
    response += f"  • Create order with new price: `create_order_tool(book_title='{result['title']}', customer_input='1', quantity=1)`\n"
    response += f"  • Check similar books: `find_books_tool(q='{current_book['author']}', by='author')`\n"
    
    return response

@tool
def order_status_tool(order_id: int) -> str:
    """
    Check the status of an order.
    
    CROSS-FUNCTION RELATIONSHIPS:
    1. With create_order_tool: Verify newly created orders
    2. With find_books_tool: Get details of books in order
    3. With inventory_summary_tool: Check stock of ordered items
    4. With restock_book_tool: Restock items from the order
    5. With update_price_tool: Check prices of ordered items
    
    When used together:
    - create_order_tool + order_status_tool: Create order then verify it
    - order_status_tool + find_books_tool: Check order then get book details
    - order_status_tool + inventory_summary_tool: Check order then inventory
    - order_status_tool + restock_book_tool: Check order then restock items
    
    Args:
        order_id: Order ID number
    
    Returns:
        Formatted order details and status
    """
    result = order_status(order_id)
    
    if "error" in result:
        return f"Error: {result['error']}"
    
    # Get current stock for each book
    stock_info = ""
    inventory_suggestions = ""
    if 'items' in result:
        for item in result['items']:
            book_search = find_books(item['title'], by="title")
            if book_search:
                current_stock = book_search[0]['stock']
                stock_info += f"    • '{item['title']}': {current_stock} copies\n"
                if current_stock < 3:
                    inventory_suggestions += f"    ⚠️ '{item['title']}' is low! Restock: `restock_book_tool(isbn='{book_search[0]['isbn']}', quantity=10)`\n"
    
    # Build response
    response = f"**Order #{order_id} Status**\n\n"
    response += f"Order Summary:\n"
    response += f"  • Status: {result['status']}\n"
    response += f"  • Customer: {result.get('customer_name', 'Unknown')}\n"
    response += f"  • Date: {result['created_at']}\n"
    response += f"  • Total Amount: ${result['total_amount']:.2f}\n"
    response += f"  • Items: {len(result.get('items', []))}\n\n"
    
    if 'items' in result:
        response += f"🛒 Order Items:\n"
        for i, item in enumerate(result['items'], 1):
            qty = item.get('qty', 1)
            subtotal = item['price'] * qty
            response += f"  {i}. {item['title']} by {item['author']}\n"
            response += f"     Qty: {qty}, Price: ${item['price']:.2f}, Subtotal: ${subtotal:.2f}\n"
    
    if stock_info:
        response += f"\nCurrent Stock Levels:\n{stock_info}"
    
    if inventory_suggestions:
        response += f"\nInventory Suggestions:\n{inventory_suggestions}"
    
    # Suggest related actions
    response += f"\nRelated Actions:\n"
    response += f"  • Create similar order: `create_order_tool(book_title='{result['items'][0]['title'] if result.get('items') else 'Clean Code'}', customer_input='{result.get('customer_id', 1)}', quantity=1)`\n"
    response += f"  • Check inventory: `inventory_summary_tool(threshold=5)`\n"
    response += f"  • Find similar books: `find_books_tool(q='{result['items'][0]['author'] if result.get('items') else 'Robert Martin'}', by='author')`\n"
    
    return response

@tool
def inventory_summary_tool(threshold: int = 5) -> str:
    """
    Get a summary of inventory status.
    
    CROSS-FUNCTION RELATIONSHIPS:
    1. With find_books_tool: Get details of low-stock books
    2. With restock_book_tool: Restock identified low-stock items
    3. With create_order_tool: Check availability before ordering
    4. With update_price_tool: Update prices of low/high stock items
    5. With order_status_tool: Check orders affecting inventory
    
    When used together:
    - inventory_summary_tool + find_books_tool: Get summary then book details
    - inventory_summary_tool + restock_book_tool: Identify then restock low items
    - inventory_summary_tool + create_order_tool: Check inventory then create order
    - inventory_summary_tool + update_price_tool: Analyze then adjust prices
    
    Args:
        threshold: Stock level threshold for low stock alert (default: 5)
    
    Returns:
        Formatted inventory summary
    """
    result = inventory_summary(threshold)
    
    if isinstance(result, dict) and "error" in result:
        return f"❌ Error: {result['error']}"
    
    low_stock_details = ""
    restock_suggestions = ""
    if result['low_stock_books']:
        for i, book in enumerate(result['low_stock_books'][:3], 1):  # Top 3 only
            low_stock_details += f"  {i}. **{book['title']}** by {book['author']}\n"
            low_stock_details += f"     ISBN: {book['isbn']}, Stock: {book['stock']}, Price: ${book['price']:.2f}\n"
            restock_suggestions += f"  • Restock '{book['title']}': `restock_book_tool(isbn='{book['isbn']}', quantity=10)`\n"
    
    response = f"**Inventory Summary**\n\n"
    response += f"Overview:\n"
    response += f"  • Total books: {result['total_books']}\n"
    response += f"  • Total inventory value: ${result['total_inventory_value']:.2f}\n"
    response += f"  • Out of stock: {result['out_of_stock_count']} books\n"
    response += f"  • Low stock (≤{threshold}): {result['low_stock_count']} books\n\n"
    
    if low_stock_details:
        response += f"📉 Top Low-Stock Books:\n{low_stock_details}\n"
    
    # Health assessment
    response += f"Inventory Health:\n"
    if result['out_of_stock_count'] > 0:
        response += f" {result['out_of_stock_count']} book(s) are OUT OF STOCK - Urgent action needed!\n"
    if result['low_stock_count'] > 0:
        response += f"{result['low_stock_count']} book(s) are running low - Consider restocking\n"
    if result['out_of_stock_count'] == 0 and result['low_stock_count'] == 0:
        response += f"  ✅ All books are sufficiently stocked\n"
    
    if restock_suggestions:
        response += f"\nRestock Suggestions:\n{restock_suggestions}"
    
    # Suggest related actions
    response += f"\nRelated Actions:\n"
    response += f"  • Check specific book: `find_books_tool(q='Clean Code', by='title')`\n"
    response += f"  • Create order: `create_order_tool(book_title='The Pragmatic Programmer', customer_input='1', quantity=1)`\n"
    response += f"  • Update prices: `update_price_tool(isbn='9780132350884', new_price=45.00)`\n"
    
    return response

# List of all tools
TOOLS = [
    find_books_tool,
    create_order_tool,
    restock_book_tool,
    update_price_tool,
    order_status_tool,
    inventory_summary_tool
]