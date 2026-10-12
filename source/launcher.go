//go:build windows

// VRC Chatbox Windows EXE launcher for the original Python/Flask service.
// The original OSC server logic is never reimplemented in Go.
package main

import (
 "errors"
 "fmt"
 "net"
 "os"
 "os/exec"
 "os/signal"
 "path/filepath"
 "strings"
 "time"
)

const serverURL = "http://127.0.0.1:5000/"
const version = "1.4.0"

func logf(format string, a ...any) { fmt.Printf("[VRC Chatbox] "+format+"\n", a...) }

func pythonOk(binary string, arguments ...string) bool {
 args := append(append([]string{},arguments...),"-c", "import sys; assert sys.version_info >= (3,10); print(sys.executable)")
 cmd := exec.Command(binary, args...)
 out,err := cmd.CombinedOutput()
 return err == nil && len(strings.TrimSpace(string(out))) > 0
}

type pythonCommand struct {binary string; args []string}

func findPython() (pythonCommand,error) {
 choices := []pythonCommand{
  {"py",[]string{"-3"}},
  {"python",nil},
  {"python3",nil},
 }
 for _,v:=range choices {
  if pythonOk(v.binary,v.args...) {return v,nil}
 }
 return pythonCommand{},errors.New("Python 3.10+ is not installed or not available in PATH")
}

func runPy(p pythonCommand, args ...string) error {
 cmd := exec.Command(p.binary,append(append([]string{},p.args...),args...)...)
 cmd.Stdin=os.Stdin;cmd.Stdout=os.Stdout;cmd.Stderr=os.Stderr
 return cmd.Run()
}

func ready() bool {conn,err:=net.DialTimeout("tcp","127.0.0.1:5000",200*time.Millisecond);if err!=nil{return false};conn.Close();return true}



func main(){
 if len(os.Args)>1 && os.Args[1]=="--version" {fmt.Println(version);return}
 base,err:=os.Executable()
 if err!=nil{logf("Cannot locate launcher: %v",err);wait();return}
 base=filepath.Dir(base)
 if strings.HasPrefix(base,"\\\\?"){base=strings.TrimPrefix(base,"\\\\?")}
 os.Chdir(base)
 script:=filepath.Join(base,"HTML osc chat","osc_viewer.py")
 reqs:=filepath.Join(base,"requirements.txt")
 if _,err=os.Stat(script);err!=nil{logf("Missing server file: %s",script);wait();return}
 if _,err=os.Stat(reqs);err!=nil{logf("Missing requirements.txt");wait();return}
 logf("Windows launcher v%s - VRChat companion",version)
 envPy:=filepath.Join(base,".venv","Scripts","python.exe")
 if _,err=os.Stat(envPy);err!=nil {
  p,found:=findPython()
  if found!=nil {
   logf("ERROR: %v",found)
   logf("Install Python 3.10+ from https://www.python.org/downloads/windows/ and enable Add python.exe to PATH")
   wait();return
  }
  logf("First start: preparing isolated Python environment...")
  if err=runPy(p,"-m","venv",filepath.Join(base,".venv"));err!=nil{logf("Environment creation failed: %v",err);wait();return}
 }
 check:=exec.Command(envPy,"-c","import flask, pythonosc, waitress")
 if err=check.Run();err!=nil{
  logf("Installing Flask + python-osc (Internet connection required on first install)...")
  pip:=exec.Command(envPy,"-m","pip","install","-r",reqs)
  pip.Stdout=os.Stdout;pip.Stderr=os.Stderr
  if err=pip.Run();err!=nil{logf("Dependency installation failed: %v",err);wait();return}
 }
 logf("Starting VRC Chatbox")
 logf("Enable OSC in VRChat. Press Ctrl+C or close this console to stop.")
 child:=exec.Command(envPy,script)
 child.Dir=filepath.Dir(script)
 child.Stdout=os.Stdout;child.Stderr=os.Stderr;child.Stdin=os.Stdin
 if err=child.Start();err!=nil{logf("Cannot launch server: %v",err);wait();return}
 defer func(){if child.Process!=nil {child.Process.Kill()}}()
 signals:=make(chan os.Signal,1);signal.Notify(signals,os.Interrupt)
 done:=make(chan error,1)
 go func(){done<-child.Wait()}()
 select{
 case s:=<-signals: logf("Received %s. Stopping server...",s);child.Process.Kill();<-done
 case err:=<-done:if err!=nil{logf("Server stopped: %v",err)}else{logf("Server stopped.")};wait()
 }
}
func wait(){fmt.Println("Press Enter to close this window...");fmt.Scanln()}
