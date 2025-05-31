document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.querySelector('.toggle-btn');
    
    // Toggle sidebar
    toggleBtn.addEventListener('click', function() {
        sidebar.classList.toggle('expand');
    });

    // Add active class to current page link
    const currentPath = window.location.pathname;
    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    
    sidebarLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });

    // Handle window resize
    function handleResize() {
        if (window.innerWidth < 768) {
            sidebar.classList.remove('expand');
        }
    }

    window.addEventListener('resize', handleResize);
    handleResize(); // Initial check
});
