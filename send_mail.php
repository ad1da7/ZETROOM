<?php
$data = json_decode(file_get_contents('php://input'), true);
if (!$data || ($data['token'] ?? '') !== 'ZETROOM_SECRET_KEY_2026') {
    http_response_code(403);
    exit('Invalid token');
}

$to = $data['to'];
$subject = '=?UTF-8?B?' . base64_encode($data['subject']) . '?=';
$body = $data['body'];
$headers = "From: Zetroom <zetroom@zetroom.ru>\r\n" .
           "Reply-To: zetroom@zetroom.ru\r\n" .
           "MIME-Version: 1.0\r\n" .
           "Content-Type: text/plain; charset=UTF-8\r\n";

if (mail($to, $subject, $body, $headers, '-f zetroom@zetroom.ru')) {
    echo 'OK';
} else {
    http_response_code(500);
    echo 'FAIL';
}
