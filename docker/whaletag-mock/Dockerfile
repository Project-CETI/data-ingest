FROM alpine:3.20

RUN apk add --no-cache openssh-server sudo bash coreutils && \
    adduser -D -s /bin/bash pi && \
    echo "pi:ceticeti" | chpasswd && \
    echo "pi ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers && \
    ssh-keygen -A && \
    sed -i 's/^#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/^#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    echo "AllowUsers pi" >> /etc/ssh/sshd_config

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22

ENTRYPOINT ["/entrypoint.sh"]
