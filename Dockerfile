FROM flant/shell-operator:latest
RUN apk --no-cache add openssl python3 py3-requests py3-yaml
ADD hooks /hooks
