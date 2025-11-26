Inventory Management System

A simple web based inventory and invoicing application built with Flask and MySQL.
This project was originally created to manage the stock and sales workflow for a small toy store in Indonesia. It supports product management, invoice generation, and PDF exports.

Features
Inventory Management

• Add, edit, and delete products
• Track stock, cost price, and selling price
• Store product category and supplier information
• Search products dynamically without reloading the page

Invoice Module

• Create invoices with multiple line items
• Store customer name and timestamp
• Edit invoices and add or remove items
• Automatically calculate subtotal and total
• Export invoice as PDF

File Upload

• Support for product image uploads (PNG, JPG, JPEG, GIF)
• Secure filename handling with Werkzeug
• Automatic storage into static folder

Database

The app uses MySQL with three main tables:
• Inventory
• Invoices
• Invoice items

Technology Stack

• Python
• Flask
• MySQL
• HTML, CSS, JavaScript
• ReportLab for PDF generation
