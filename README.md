# library-desk-agent
# 1. Install dependencies
pip install -r requirements.txt
# 2. Create database with sample data
python scripts/seed_database.py

# 3. Run the application
library.db - Database Setup
# Creates SQLite database with books, customers, and orders tables
# Inserts 10 sample books and 6 sample customers
# Creates: db/library.db
python scripts/seed_database.py
# Output: ✅ Database seeded with 10 books and 6 customers

python frontend.py - Application Launcher
# Launches the Library Desk GUI
# Starts the AI agent with tool calling capabilities
Run it:

📊 What Gets Seeded
Books Table (10 entries)
Clean Code (ISBN: 9780132350884, Stock: 10)

The Pragmatic Programmer (ISBN: 9780201616224, Stock: 5)

The C Programming Language (ISBN: 9780131103627, Stock: 7)

Fluent Python (ISBN: 9781491957660, Stock: 6)

Introduction to Algorithms (ISBN: 9780262033848, Stock: 4)

Effective Java (ISBN: 9780134685991, Stock: 8)

Designing Data-Intensive Applications (ISBN: 9781492078005, Stock: 3)

Clean Architecture (ISBN: 9780134494166, Stock: 9)

Spring in Action (ISBN: 9781617296086, Stock: 5)

Python Data Science Handbook (ISBN: 9781492055020, Stock: 6)

Customers Table (6 entries)
Ahmad Mahmoud (ahmad@mail.com)

Sara Khaled (sara@mail.com)

Omar Hassan (omar@mail.com)

Lina Youssef (lina@mail.com)

Yousef Nasser (yousef@mail.com)

Maya Adel (maya@mail.com)

Sample Orders (4 orders)
Order #1: Ahmad bought 2× Clean Code + 1× Effective Java

Order #2: Sara bought 1× Pragmatic Programmer + 2× Designing Data-Intensive Applications

Order #3: Omar bought 1× The C Programming Language

Order #4: Lina bought 1× Fluent Python
