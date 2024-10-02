# ppm-gateway

VS Code : virtualenv
Cmd + Shift + P : Python create terminal
pip install virtualenv
virtualenv .venv

-rtsp_transport   tcp -i ${channel[$i]} -fflags flush_packets -max_delay 1 -an -flags -global_header -hls_time 2  -hls_list_size 5  -hls_wrap 10  -vcodec copy -s 216x384 -b 1024k -y  /video/$i.m3u8  >/dev/null 2>&1 &
done
