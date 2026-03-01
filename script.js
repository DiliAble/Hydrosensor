// Initialize map
const map = L.map('map').setView([41.311081, 69.240562], 12); // Default to Tashkent

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

// Load devices and populate table/map
function loadDevices(regionId = '', districtId = '') {
    fetch(`/api/devices?region_id=${regionId}&district_id=${districtId}`)
        .then(response => response.json())
        .then(data => {
            const tableBody = document.querySelector('#devicesTable tbody');
            tableBody.innerHTML = '';
            
            // Clear existing markers
            map.eachLayer((layer) => {
                if (layer instanceof L.Marker) {
                    map.removeLayer(layer);
                }
            });

            data.forEach(device => {
                // Add to table
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${device.device_id}</td>
                    <td>${device.name}</td>
                    <td>${device.region}</td>
                    <td>${device.district}</td>
                    <td><span class="badge bg-secondary">${device.token}</span></td>
                    <td>
                        <span class="badge ${device.is_active ? 'bg-success' : 'bg-danger'}">
                            ${device.is_active ? 'Faol' : 'Nofaol'}
                        </span>
                    </td>
                    <td>
                        <button class="btn btn-warning btn-sm btn-icon" onclick="editDevice(${device.id})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <a href="/delete_device/${device.id}" class="btn btn-danger btn-sm btn-icon" onclick="return confirm('O\'chirishni tasdiqlaysizmi?')">
                            <i class="fas fa-trash"></i>
                        </a>
                    </td>
                `;
                tableBody.appendChild(row);

                // Add to map if coordinates exist
                if (device.lat && device.lng) {
                    L.marker([device.lat, device.lng])
                        .addTo(map)
                        .bindPopup(`<b>${device.name}</b><br>ID: ${device.device_id}`);
                }
            });
        });
}

// Load districts dynamically
function loadDistricts(regionId, targetSelectId) {
    const select = document.getElementById(targetSelectId);
    select.innerHTML = '<option value="">Tanlang</option>';
    
    if (regionId) {
        fetch(`/api/districts/${regionId}`)
            .then(response => response.json())
            .then(data => {
                data.forEach(district => {
                    const option = document.createElement('option');
                    option.value = district.id;
                    option.textContent = district.name;
                    select.appendChild(option);
                });
            });
    }
}

// Filter devices
function filterDevices() {
    const regionId = document.getElementById('filterRegion').value;
    const districtId = document.getElementById('filterDistrict').value;
    loadDevices(regionId, districtId);
}

// Edit device modal population (simplified for demo)
function editDevice(id) {
    // In a real app, you'd fetch the single device details first
    // For now, we'll just redirect to a placeholder or show the modal
    // This part would need a specific API endpoint to get device details by ID
    // to pre-fill the form.
    // For this example, let's assume we have the data or fetch it.
    
    // Placeholder logic:
    const modal = new bootstrap.Modal(document.getElementById('editDeviceModal'));
    const form = document.getElementById('editDeviceForm');
    form.action = `/edit_device/${id}`;
    modal.show();
}

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    loadDevices();
});
