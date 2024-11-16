import usocket
import ssl
import ujson


def send_post_request(url, data):
    # URL の解析
    proto, _, host, path = url.split("/", 3)
    addr_info = usocket.getaddrinfo(host, 443, 0, usocket.SOCK_STREAM)[0]

    # ソケット作成と接続
    sock = usocket.socket(addr_info[0], addr_info[1], addr_info[2])
    sock.connect(addr_info[4])

    # ソケットを SSL でラップ
    sock = ssl.wrap_socket(sock)

    # POST リクエストの作成
    request_body = ujson.dumps(data)
    headers = (
        f"POST /{path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(request_body)}\r\n"
        f"Connection: close\r\n\r\n"
    )

    # リクエスト送信
    sock.write(headers.encode("utf-8") + request_body.encode("utf-8"))

    # レスポンスを受信
    response = b""
    while True:
        chunk = sock.read(1024)
        if not chunk:
            break
        response += chunk

    sock.close()
    return response


if __name__ == "__main__":
    # 使用例
    url = "https://asia-northeast1-jphacks-ben-tech.cloudfunctions.net/saveHistory"
    data = {"key1": "value1", "key2": "value2"}
    response = send_post_request(url, data)
    print(response.decode("utf-8"))
