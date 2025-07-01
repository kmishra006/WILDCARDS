// Main JavaScript for SpeciScan

document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const uploadForm = document.getElementById('upload-form');
    const nameForm = document.getElementById('name-form');
    const fileInput = document.getElementById('file-input');
    const fileName = document.getElementById('file-name');
    const uploadZone = document.getElementById('upload-zone');
    const resultsContainer = document.getElementById('results');
    const loadingOverlay = document.getElementById('loading-overlay');

    // Handle drag and drop for file upload
    uploadZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', function() {
        uploadZone.classList.remove('dragover');
    });

    uploadZone.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            updateFileName();
        }
    });

    // Update file name display when file is selected
    fileInput.addEventListener('change', updateFileName);

    function updateFileName() {
        if (fileInput.files.length > 0) {
            fileName.textContent = fileInput.files[0].name;
            uploadZone.classList.add('has-file');
        } else {
            fileName.textContent = '';
            uploadZone.classList.remove('has-file');
        }
    }

    // Handle image upload form submission
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (fileInput.files.length === 0) {
            alert('Please select an image file.');
            return;
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        
        // Show loading overlay
        loadingOverlay.classList.add('active');
        
        // Submit form data to server
        fetch('/upload_image', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Hide loading overlay
            loadingOverlay.classList.remove('active');
            
            // Display results
            displayResults(data);
        })
        .catch(error => {
            // Hide loading overlay
            loadingOverlay.classList.remove('active');
            
            console.error('Error:', error);
            alert('Error: ' + error.message);
        });
    });

    // Handle species name form submission
    nameForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(nameForm);
        
        // Show loading overlay
        loadingOverlay.classList.add('active');
        
        // Submit form data to server
        fetch('/search_by_name', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Hide loading overlay
            loadingOverlay.classList.remove('active');
            
            // Display results
            displayResults(data);
        })
        .catch(error => {
            // Hide loading overlay
            loadingOverlay.classList.remove('active');
            
            console.error('Error:', error);
            alert('Error: ' + error.message);
        });
    });

    // Handle suggestion chips
    const suggestionChips = document.querySelectorAll('.chip');
    const speciesNameInput = nameForm.querySelector('input[name="species_name"]');
    
    suggestionChips.forEach(chip => {
        chip.addEventListener('click', function() {
            const speciesName = this.getAttribute('data-species');
            speciesNameInput.value = speciesName;
            nameForm.dispatchEvent(new Event('submit'));
        });
    });

    // Function to display results
    function displayResults(data) {
        // Scroll to results
        resultsContainer.scrollIntoView({ behavior: 'smooth' });
        
        // Check if we have valid data
        if (data.error) {
            resultsContainer.innerHTML = `
                <div class="error-message">
                    <h2>Error</h2>
                    <p>${data.error}</p>
                </div>
            `;
            resultsContainer.classList.add('active');
            return;
        }
        
        // Extract data
        const speciesData = data.species_data;
        const images = data.images;
        
        // Check if species data contains an error
        if (speciesData.error) {
            // If we have some basic information despite the error, display it with a notice
            if (speciesData.title) {
                let errorHtml = `
                    <div class="notice-message">
                        <p><i class="fas fa-exclamation-triangle"></i> ${speciesData.error}</p>
                    </div>
                `;
                
                // Build the complete HTML for limited results
                const resultsHtml = `
                    <div class="species-header">
                        <img src="${images && images.length > 0 && !images[0].error 
                            ? images[0].url 
                            : 'https://via.placeholder.com/300x250?text=No+Image+Available'}" 
                            alt="${speciesData.title}" class="species-img">
                        <div class="species-details">
                            <h2>${speciesData.title}</h2>
                            <p class="scientific-name">${speciesData.title}</p>
                            ${errorHtml}
                            <p>${speciesData.description || 'No description available.'}</p>
                        </div>
                    </div>
                `;
                
                // Update the results container and make it visible
                resultsContainer.innerHTML = resultsHtml;
                resultsContainer.classList.add('active');
                return;
            }
            
            resultsContainer.innerHTML = `
                <div class="error-message">
                    <h2>Error</h2>
                    <p>${speciesData.error}</p>
                </div>
            `;
            resultsContainer.classList.add('active');
            return;
        }
        
        // Build the classification table
        let classificationHtml = '';
        const classification = speciesData.classification;
        
        for (const [rank, taxon] of Object.entries(classification)) {
            if (taxon !== 'Unknown') {
                classificationHtml += `
                    <tr>
                        <th>${capitalizeFirstLetter(rank)}</th>
                        <td>${taxon}</td>
                    </tr>
                `;
            }
        }
        
        // Build fun facts HTML
        let funFactsHtml = '';
        if (speciesData.fun_facts && speciesData.fun_facts.length > 0) {
            speciesData.fun_facts.forEach(fact => {
                funFactsHtml += `<li>${fact}</li>`;
            });
        } else {
            funFactsHtml = '<li>No fun facts available.</li>';
        }
        
        // Build image gallery HTML
        let galleryHtml = '';
        if (images && images.length > 0) {
            images.forEach(image => {
                // Skip images with errors
                if (image.error) return;
                
                galleryHtml += `
                    <div class="gallery-item">
                        <img src="${image.thumb_url || image.url}" alt="${image.title}" class="gallery-img">
                        <div class="gallery-caption">
                            <p>${image.description || 'No description available'}</p>
                            <small>By: ${image.author}</small>
                        </div>
                    </div>
                `;
            });
        } else {
            galleryHtml = '<p>No images available.</p>';
        }
        
        // Get the main image from the first gallery image or use a placeholder
        const mainImageUrl = images && images.length > 0 && !images[0].error
            ? images[0].url
            : 'https://via.placeholder.com/300x250?text=No+Image+Available';
        
        // Build the complete HTML for results
        const resultsHtml = `
            <div class="species-header">
                <img src="${mainImageUrl}" alt="${speciesData.title}" class="species-img">
                <div class="species-details">
                    <h2>${speciesData.title}</h2>
                    <p class="scientific-name">${speciesData.title}</p>
                    <p>${speciesData.description || 'No description available.'}</p>
                </div>
            </div>
            
            <div class="species-info">
                <div class="info-card">
                    <h3><i class="fas fa-sitemap"></i> Classification</h3>
                    <table class="classification-table">
                        ${classificationHtml}
                    </table>
                </div>
                
                <div class="info-card">
                    <h3><i class="fas fa-tree"></i> Habitat</h3>
                    <p>${speciesData.habitat || 'Habitat information not available.'}</p>
                </div>
                
                <div class="info-card">
                    <h3><i class="fas fa-lightbulb"></i> Fun Facts</h3>
                    <ul class="info-list">
                        ${funFactsHtml}
                    </ul>
                </div>
            </div>
            
            <div class="gallery">
                <h3><i class="fas fa-images"></i> Gallery</h3>
                <div class="gallery-grid">
                    ${galleryHtml}
                </div>
            </div>
            
            ${speciesData.data_sources ? 
                `<div class="data-sources">
                    <p><small>Data sources: ${speciesData.data_sources.join(', ')}</small></p>
                </div>` : ''}
        `;
        
        // Update the results container and make it visible
        resultsContainer.innerHTML = resultsHtml;
        resultsContainer.classList.add('active');
    }

    // Helper function to capitalize the first letter of a string
    function capitalizeFirstLetter(string) {
        return string.charAt(0).toUpperCase() + string.slice(1);
    }
});