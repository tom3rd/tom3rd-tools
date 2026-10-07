// 문의 폼: 받는 주소가 정해지면 CONTACT_EMAIL에 넣으세요. 비어 있으면 전송하지 않고 안내만 표시합니다.
const CONTACT_EMAIL = "";
const form = document.getElementById("contact-form");
const status = document.getElementById("status");
form.addEventListener("submit", (e) => {
  e.preventDefault();
  if (!form.checkValidity()) { status.textContent = "이름, 이메일, 내용을 모두 입력해 주세요."; return; }
  if (!CONTACT_EMAIL) { status.textContent = "문의 접수 주소가 아직 연결되지 않았습니다. 운영자에게 직접 연락해 주세요."; return; }
  const d = new FormData(form);
  const body = encodeURIComponent(`${d.get("message")}\n\n보낸 사람: ${d.get("name")} <${d.get("email")}>`);
  location.href = `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent("[tom3rd.com] " + d.get("type"))}&body=${body}`;
  status.textContent = "메일 앱이 열립니다. 보내기를 눌러야 전달됩니다.";
});
