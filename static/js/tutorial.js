document.addEventListener('DOMContentLoaded', function() {
    // Fetch market status
    fetchMarketStatus();
    
    // Load tutorial steps
    fetch('/api/tutorial/content')
        .then(response => response.json())
        .then(data => {
            const stepsDiv = document.getElementById('tutorialSteps');
            stepsDiv.innerHTML = data.map((step, idx) => `
                <div class="card mb-3">
                    <div class="card-header bg-light">
                        <strong>${idx + 1}. ${step.title}</strong>
                    </div>
                    <div class="card-body">${step.body}</div>
                </div>
            `).join('');
        })
        .catch(error => {
            console.error('Error loading tutorial content:', error);
            document.getElementById('tutorialSteps').innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    Error loading tutorial content. Please try refreshing the page.
                </div>
            `;
        });

    // Load terms
    fetch('/api/tutorial/terms')
        .then(response => response.json())
        .then(data => {
            const termsDiv = document.getElementById('termsList');
            termsDiv.innerHTML = data.map(term => `
                <div class="mb-3">
                    <strong>${term.term}:</strong> ${term.definition}
                </div>
            `).join('');
        })
        .catch(error => {
            console.error('Error loading terms:', error);
            document.getElementById('termsList').innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    Error loading terms. Please try refreshing the page.
                </div>
            `;
        });
        
    // Fetch market status
    function fetchMarketStatus() {
        fetch('/api/markets')
            .then(response => response.json())
            .then(data => {
                const marketStatus = document.getElementById('marketStatus');
                if (data.is_open) {
                    marketStatus.innerHTML = 'Market Status: <span class="text-success">Open</span>';
                } else {
                    const nextOpen = new Date(data.next_open);
                    marketStatus.innerHTML = `Market Status: <span class="text-danger">Closed</span> (Opens ${formatDateTime(nextOpen)})`;
                }
            })
            .catch(error => {
                console.error('Error fetching market status:', error);
                document.getElementById('marketStatus').textContent = 'Market Status: Unknown';
            });
    }
    
    // Utility: Format date and time
    function formatDateTime(date) {
        return date.toLocaleString();
    }
});
