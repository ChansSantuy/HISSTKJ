// Ambil data dari global
const { user, current_user } = window.appConfig;

// Set fullname
document.getElementById("nav_fullname").textContent = user.nama;

// Format kelas
let kelasFormatted = (user.kelas || "").replace(" ", "-");

// Role → label
let infoText = kelasFormatted;
if (user.role === "siswa") {
  infoText += " • Student";
} else if (user.role === "admin") {
  infoText += " • Admin";
}
document.getElementById("nav_info").textContent = infoText;

// Avatar handler
fetch(`/static/data/data_user/${current_user}/avatar/default.json`)
  .then(res => res.ok ? res.json() : Promise.reject("No default avatar"))
  .then(data => {
    document.getElementById("nav_avatar").src = data.link;
  })
  .catch(() => {
    document.getElementById("nav_avatar").src = `/static/data/data_user/${current_user}/avatar/avatar.jpg`;
  });
