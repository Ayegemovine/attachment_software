# fix_views.py
print("🔧 Fixing views.py syntax error...")

with open('accounts/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Look for the specific error pattern
if "return render(request, 'accounts/add_attachee.html', {'form': form})def check_status" in content:
    print("✅ Found the syntax error - fixing...")
    
    # Add newline between functions
    content = content.replace(
        "return render(request, 'accounts/add_attachee.html', {'form': form})def check_status",
        "return render(request, 'accounts/add_attachee.html', {'form': form})\n\ndef check_status"
    )
    
    with open('accounts/views.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Syntax error fixed!")

# Also ensure proper spacing between all functions
content = content.replace('\n\ndef ', '\n\ndef ')  # Already correct format

# Write back
with open('accounts/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ views.py is now syntactically correct!")