import pygsheets
import ffmpeg
import subprocess
import os 
import signal

def subp():
    pull_url = 'rtsp://admin:Az123567@192.168.18.7:7001/bbf6e391-beb5-828a-64f7-86677fb65430'
    push_url = 'rtsp://127.0.0.1:8554/stream/h1'
    command = ['ffmpeg',
                '-rtsp_transport', 'tcp',
                '-i', pull_url,
                '-c', 'copy',
                '-f', 'rtsp',
                '-preset', 'ultrafast',
                push_url]
    #process = subprocess.run(command)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    print (process.pid)
    process.kill()
    
    #process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True, preexec_fn=os.setsid)
    
    
    #if process.returncode == 0 :
    #ffmpeg -rtsp_transport tcp -i rtsp://admin:Az123567@192.168.18.7:7001/bbf6e391-beb5-828a-64f7-86677fb65430 \
    #-preset ultrafast \
    #-c copy -f rtsp rtsp://127.0.0.1:8554/stream/h1 

def readGoogleSheet(sheet_key):
    client = pygsheets.authorize(service_account_file='client_secret.json')
    sheet = client.open_by_key(sheet_key)
    work_sheet = sheet.worksheet_by_title('Dashboard')

    dashboardList = work_sheet.get_values('B2', 'B')
    g_table = work_sheet.get_values('A2', 'N')
    
    


if __name__ == '__main__':
    subp()