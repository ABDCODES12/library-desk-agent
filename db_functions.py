# db_functions.py
import sqlite3
import json
from typing import List, Dict, Optional
from datetime import datetime
import os



path = r"db/library.db"
def set_current_session(session_id: str):
    global CURRENT_SESSION_ID
    CURRENT_SESSION_ID = session_id


def get_connection():
    """Get a new database connection"""
    return sqlite3.connect(path)

def find_books(q: str, by: str = "title") -> List[Dict]:
    """Find books by title or author"""
    by = by.lower()
    if by not in ["title", "author"]:
        by = "title"
    
    conn = get_connection()
    conn.row_factory = sqlite3.Row  # Enable row factory
    cursor = conn.cursor()
    
    cursor.execute(
        f"""SELECT isbn, title, author, price, stock FROM books WHERE {by} LIKE ?""", 
        (f"%{q}%",)
    )
    
    rows = cursor.fetchall()
    results = []
    for row in rows:
        results.append(dict(row))
    
    conn.close()
    return results

def create_order(customer_id: int, items: List[Dict]) -> Dict:
    """Create a new order and reduce stock"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Start transaction
        conn.execute("BEGIN TRANSACTION")
        
        # Get book details first to track stock changes
        stock_changes = {}
        
        # Validate all items first
        for item in items:
            isbn = item["isbn"]
            qty = item["qty"]
            
            # Check if book exists and has enough stock
            cursor.execute(
                "SELECT title, stock FROM books WHERE isbn = ?", 
                (isbn,)
            )
            book = cursor.fetchone()
            
            if not book:
                raise ValueError(f"Book with ISBN {isbn} not found")
            
            title, stock = book
            
            if stock < qty:
                raise ValueError(
                    f"Insufficient stock for '{title}'. Available: {stock}, Requested: {qty}"
                )
            
            # Store stock changes
            stock_changes[isbn] = {
                "title": title,
                "old_stock": stock,
                "new_stock": stock - qty
            }
        
        # Create order
        cursor.execute(
            "INSERT INTO orders (customer_id, status) VALUES (?, ?)", 
            (customer_id, 'created')
        )
        order_id = cursor.lastrowid
        
        # Process each item and reduce stock
        for item in items:
            isbn = item["isbn"]
            qty = item["qty"]
            
            # Insert order item
            cursor.execute(
                "INSERT INTO order_items (order_id, isbn, qty) VALUES (?, ?, ?)",
                (order_id, isbn, qty)
            )
            
            # Reduce stock
            cursor.execute(
                "UPDATE books SET stock = stock - ? WHERE isbn = ?", 
                (qty, isbn)
            )
        
        conn.commit()
        
        # Calculate total amount
        total_amount = 0.0
        for item in items:
            cursor.execute("SELECT price FROM books WHERE isbn = ?", (item["isbn"],))
            price = cursor.fetchone()[0]
            total_amount += price * item["qty"]
        
        # Get final stock levels
        final_stock_info = []
        for isbn, change in stock_changes.items():
            cursor.execute("SELECT stock FROM books WHERE isbn = ?", (isbn,))
            final_stock = cursor.fetchone()[0]
            final_stock_info.append({
                "title": change["title"],
                "isbn": isbn,
                "old_stock": change["old_stock"],
                "new_stock": final_stock
            })
        
        # Log tool call
        save_tool_call("default_session", "create_order", 
                      {"customer_id": customer_id, "items": items},
                      {"order_id": order_id, "total_amount": total_amount, "stock_changes": final_stock_info})
        
        return {
            "order_id": order_id,
            "customer_id": customer_id,
            "total_amount": total_amount,
            "status": "created",
            "items": items,
            "stock_changes": final_stock_info, 
            "message": f"Order #{order_id} created successfully"
        }
        
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        conn.close()
def restock_book(isbn: str, qty: int) -> Dict:
    """Restock a book by ISBN"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Check if book exists
        cursor.execute("SELECT title, stock FROM books WHERE isbn = ?", (isbn,))
        book = cursor.fetchone()
        
        if not book:
            return {"error": f"Book with ISBN {isbn} not found"}
        
        title, old_stock = book
        
        # Update stock
        cursor.execute(
            "UPDATE books SET stock = stock + ? WHERE isbn = ?", 
            (qty, isbn)
        )
        conn.commit()
        
        cursor.execute("SELECT stock FROM books WHERE isbn = ?", (isbn,))
        new_stock = cursor.fetchone()[0]
        save_tool_call("default_session", "restock_book",
                      {"isbn": isbn, "qty": qty},
                      {"title": title, "new_stock": new_stock})
        
        return {
            "isbn": isbn,
            "title": title,
            "old_stock": old_stock,
            "new_stock": new_stock,
            "added": qty,
            "message": f"Restocked {title} by {qty} copies. New stock: {new_stock}"
        }
        
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

def update_price(isbn: str, price: float) -> Dict:
    """Update book price"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Check if book exists
        cursor.execute("SELECT title FROM books WHERE isbn = ?", (isbn,))
        book = cursor.fetchone()
        
        if not book:
            return {"error": f"Book with ISBN {isbn} not found"}
        
        title = book[0]
        
        # Get old price
        cursor.execute("SELECT price FROM books WHERE isbn = ?", (isbn,))
        old_price = cursor.fetchone()[0]
        
        # Update price
        cursor.execute("UPDATE books SET price = ? WHERE isbn = ?", (price, isbn))
        conn.commit()
        
        # Log tool call
        save_tool_call("default_session", "update_price",
                      {"isbn": isbn, "price": price},
                      {"title": title, "old_price": old_price, "new_price": price})
        
        return {
            "isbn": isbn,
            "title": title,
            "old_price": old_price,
            "new_price": price,
            "message": f"Updated price of {title} from ${old_price:.2f} to ${price:.2f}"
        }
        
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

def order_status(order_id: int) -> Dict:
    """Check order status"""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Get order details
        cursor.execute("""
            SELECT o.id, o.customer_id, o.status, o.created_at,
                   c.name, c.email
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            WHERE o.id = ?
        """, (order_id,))
        
        order = cursor.fetchone()
        
        if not order:
            return {"error": f"Order with ID {order_id} not found"}
        
        order_data = dict(order)
        
        # Get order items and calculate total
        cursor.execute("""
            SELECT b.isbn, b.title, b.author, b.price, oi.qty
            FROM order_items oi
            JOIN books b ON oi.isbn = b.isbn
            WHERE oi.order_id = ?
        """, (order_id,))
        
        items = []
        total_amount = 0.0
        
        for row in cursor.fetchall():
            item = dict(row)
            subtotal = item["price"] * item["qty"]
            total_amount += subtotal
            item["subtotal"] = subtotal
            items.append(item)
        
        # Return with proper field names
        return {
            "order_id": order_data["id"],
            "customer_id": order_data["customer_id"],
            "status": order_data["status"],
            "created_at": order_data["created_at"],
            "customer_name": order_data["name"],  
            "customer_email": order_data["email"],
            "total_amount": total_amount,
            "items": items,
            "item_count": len(items),
            "total_items": sum(item["qty"] for item in items)
        }
        
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

def inventory_summary(threshold: int = 5) -> Dict:
    """Get inventory summary"""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT isbn, title, author, price, stock 
            FROM books 
            WHERE stock <= ? 
            ORDER BY stock ASC
        """, (threshold,))
        
        low_stock = [dict(row) for row in cursor.fetchall()]
        
        # Get total inventory value
        cursor.execute("SELECT SUM(price * stock) FROM books")
        total_value = cursor.fetchone()[0] or 0.0
        
        # Get total books count
        cursor.execute("SELECT COUNT(*) FROM books")
        total_books = cursor.fetchone()[0]
        
        # Get out of stock books
        cursor.execute("SELECT COUNT(*) FROM books WHERE stock = 0")
        out_of_stock = cursor.fetchone()[0]
        
        return {
            "total_books": total_books,
            "total_inventory_value": round(total_value, 2),
            "low_stock_threshold": threshold,
            "low_stock_count": len(low_stock),
            "out_of_stock_count": out_of_stock,
            "low_stock_books": low_stock,
            "summary": f"Total {total_books} books worth ${total_value:.2f}, {len(low_stock)} books below threshold ({threshold})"
        }
        
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

def save_message(session_id: str, role: str, content: str):
    """Save a chat message to the database"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content)
        )
        conn.commit()
    except Exception as e:
        print(f"Note: Could not save message - {e}")
    finally:
        conn.close()

def save_tool_call(session_id: str, name: str, args: dict, result: dict):
    """Save a tool call to the database"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO tool_calls (session_id, name, args_json, result_json) VALUES (?, ?, ?, ?)",
            (session_id, name, json.dumps(args), json.dumps(result))
        )
        conn.commit()
    except Exception as e:
        print(f"Note: Could not save tool call - {e}")
    finally:
        conn.close()

def get_chat_history(session_id: str, limit: int = 10) -> List[Dict]:
    """Get chat history for a session"""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
            (session_id, limit)
        )
        rows = cursor.fetchall()
        
        history = [{"role": row["role"], "content": row["content"]} for row in rows]
        return history
    except Exception as e:
        print(f"Note: Could not get chat history - {e}")
        return []
    finally:
        conn.close()

def get_customer_id(customer_input: str) -> Optional[int]:
    """Convert customer input to customer ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Check if input is numeric ID
        if customer_input.isdigit():
            cursor.execute("SELECT id FROM customers WHERE id = ?", (int(customer_input),))
            row = cursor.fetchone()
            if row:
                return row[0]
        
        # Check if input contains "customer" prefix
        if "customer" in customer_input.lower():
            try:
                parts = customer_input.lower().split()
                if len(parts) > 1 and parts[1].isdigit():
                    customer_id = int(parts[1])
                    cursor.execute("SELECT id FROM customers WHERE id = ?", (customer_id,))
                    row = cursor.fetchone()
                    if row:
                        return row[0]
            except:
                pass
        
        # Try matching by name
        cursor.execute("SELECT id FROM customers WHERE name LIKE ?", (f"%{customer_input}%",))
        row = cursor.fetchone()
        
        return row[0] if row else None
        
    except Exception as e:
        print(f"Error getting customer ID: {e}")
        return None
    finally:
        conn.close()

def get_isbn_by_title(title: str) -> Optional[str]:
    """Get ISBN by book title"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT isbn FROM books WHERE title LIKE ?", (f"%{title}%",))
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception as e:
        print(f"Error getting ISBN: {e}")
        return None
    finally:
        conn.close()