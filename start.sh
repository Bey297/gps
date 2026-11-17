
while true; do
    ssh -o ServerAliveInterval=30 \
        -o ServerAliveCountMax=3 \
        -o ExitOnForwardFailure=yes \
        -R 80:localhost:5001 \
        nokey@localhost.run
        
    sleep 5
done
