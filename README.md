# Star Toys Inventory Management System

A full stack inventory and invoicing application built with Flask and MySQL.  
Designed as a lightweight retail management system for a small toy store, this project demonstrates CRUD operations, server side rendering, PDF generation, relational database modeling, and file handling.

## Key Highlights

- End to end inventory and sales workflow  
- Clean separation between views, routes, and database logic  
- Dynamic search using AJAX  
- PDF invoice generation using ReportLab  
- Image upload with validation and secure storage  
- Relational schema design for transactional systems  
- Full CRUD for inventory and invoice modules  

## Architecture

The application follows a simplified MVC inspired structure.

### Model  
Database interactions using MySQL Connector.

### View  
Jinja2 templates with vanilla JavaScript.

### Controller  
Flask routes that coordinate inventory and invoice logic.

## Tech Stack

**Backend**  
- Python  
- Flask  
- MySQL Connector  
- ReportLab  
- Pillow  

**Frontend**  
- HTML  
- CSS  
- JavaScript  
- Jinja2  

**Database**  
- MySQL  
- Relational transactional schema  
- Foreign key constraints  

## Features

### Inventory Module
- Add, update, delete products  
- Track stock, supplier, cost price, selling price  
- Product image upload support  
- Real time search using asynchronous requests  

### Invoice Module
- Create invoice with multiple items  
- Update or remove items in existing invoices  
- Automatic subtotal and total calculation  
- Export invoice as PDF  
- Persistent invoice history  

### File Upload Handling
- Secure file naming  
- Allowed extension validation  
- Stored under static uploads  

