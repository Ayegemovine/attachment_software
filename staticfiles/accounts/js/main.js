# Create the file
@"
// Main JavaScript file
document.addEventListener('DOMContentLoaded', function() {
    console.log('Attachment System loaded');
    
    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('is-invalid');
                    
                    if (!field.nextElementSibling || !field.nextElementSibling.classList.contains('invalid-feedback')) {
                        const errorDiv = document.createElement('div');
                        errorDiv.className = 'invalid-feedback';
                        errorDiv.textContent = 'This field is required';
                        field.parentNode.insertBefore(errorDiv, field.nextSibling);
                    }
                } else {
                    field.classList.remove('is-invalid');
                    field.classList.add('is-valid');
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                
                const alertDiv = document.createElement('div');
                alertDiv.className = 'alert alert-danger fade-in';
                alertDiv.innerHTML = '<i class="fas fa-exclamation-circle"></i> Please fill all required fields.';
                form.prepend(alertDiv);
                
                setTimeout(() => alertDiv.remove(), 5000);
            }
        });
    });
    
    // File upload preview
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const fileName = this.files[0] ? this.files[0].name : 'No file chosen';
            const parent = this.parentElement;
            
            const existingPreview = parent.querySelector('.file-preview');
            if (existingPreview) existingPreview.remove();
            
            if (this.files[0]) {
                const previewDiv = document.createElement('div');
                previewDiv.className = 'file-preview alert alert-light mt-2';
                previewDiv.innerHTML = \`
                    <i class="fas fa-file me-2"></i>
                    <strong>Selected:</strong> \${fileName}
                    <small class="text-muted ms-2">(\${(this.files[0].size / 1024 / 1024).toFixed(2)} MB)</small>
                \`;
                parent.appendChild(previewDiv);
                
                // Validate file size (5MB limit)
                if (this.files[0].size > 5 * 1024 * 1024) {
                    previewDiv.className = 'file-preview alert alert-danger mt-2';
                    previewDiv.innerHTML = \`
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        File too large! Maximum size is 5MB. Current: \${(this.files[0].size / 1024 / 1024).toFixed(2)} MB
                    \`;
                    this.value = '';
                }
            }
        });
    });
    
    // Animate stats numbers on dashboard
    const statNumbers = document.querySelectorAll('.stats-number');
    statNumbers.forEach(stat => {
        const target = parseInt(stat.textContent);
        if (!isNaN(target)) {
            let current = 0;
            const increment = target / 50;
            const timer = setInterval(() => {
                current += increment;
                if (current >= target) {
                    current = target;
                    clearInterval(timer);
                }
                stat.textContent = Math.round(current).toLocaleString();
            }, 50);
        }
    });
});
"@ | Out-File -FilePath "accounts\static\accounts\js\main.js" -Encoding UTF8