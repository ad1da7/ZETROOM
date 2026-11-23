<?php
$d = json_decode(stream_get_contents(STDIN), true);
$s = '=?UTF-8?B?' . base64_encode($d['subject']) . '?=';
$h = "From: Zetroom <zetroom@zetroom.ru>\r\nContent-Type: text/plain; charset=UTF-8\r\n";
echo mail($d['to'], $s, $d['body'], $h, '-f zetroom@zetroom.ru') ? 'OK' : 'FAIL';
