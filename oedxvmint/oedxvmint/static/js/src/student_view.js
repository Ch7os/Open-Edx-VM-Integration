$(function () {
    // Function to toggle visibility and spinner for a specific button
    function toggleButton(buttonId, showSpinner) {
        const spinner = $(buttonId + ' .loading-spinner');
        const content = $(buttonId + ' .button-content');
        if (showSpinner) {
            content.addClass('hidden-content'); // Hide text and icon
            spinner.show(); // Show spinner
        } else {
            content.removeClass('hidden-content'); // Show text and icon
            spinner.hide(); // Hide spinner
        }
    }

    // Function to set the operational state of the VM
    function setVMState(isRunning) {
        if (isRunning) {
            $('#start-vm').css('visibility', 'hidden');
            $('#stop-vm').css('visibility', 'visible');
            $('#reset-vm').css('visibility', 'visible');
        } else {
            $('#start-vm').css('visibility', 'visible');
            $('#stop-vm').css('visibility', 'hidden');
            $('#reset-vm').css('visibility', 'hidden');
            updateIP('Not Assigned'); // Reset IP when VM is not running
        }
    }

    // Function to update the IP address display
    function updateIP(newIP) {
        $('#vm-ip').show().find('span').text(newIP);
    }

    // Start VM button click event
    $('#start-vm').click(function () {
        console.log("Starting VM...");
        toggleButton('#start-vm', true);
        setTimeout(() => {
            toggleButton('#start-vm', false);
            setVMState(true);
            updateIP('192.168.1.100');  // Example IP, replace with actual data retrieval logic
        }, 3000); // Simulate start delay
    });

    // Stop VM button click event
    $('#stop-vm').click(function () {
        console.log("Stopping VM...");
        setVMState(false);
    });

    // Reset VM button click event
    $('#reset-vm').click(function () {
        console.log("Resetting VM...");
        toggleButton('#reset-vm', true);
        setTimeout(() => {
            toggleButton('#reset-vm', false);
            // Assume the VM stays running but resets to a fresh state
            setVMState(true);
            updateIP('192.168.1.100');  // Example new IP, replace as needed
        }, 3000); // Simulate reset delay
    });
});