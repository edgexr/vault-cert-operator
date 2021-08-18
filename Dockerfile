FROM flant/shell-operator:latest
RUN apk --no-cache add python3 py3-requests
ADD hooks /hooks
