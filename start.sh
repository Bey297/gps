while true; do
    ssh -o ServerAliveInterval=30 \
        -o ServerAliveCountMax=3 \
        -o ExitOnForwardFailure=yes \
        -R 80:localhost:5001 \
        nokey@localhost.run 2>&1 | grep --line-buffered '\.lhr\.life'

    sleep 5
done
