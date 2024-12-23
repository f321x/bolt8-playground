Python script to transfer data over the bolt 8 noise protocol. 

This has no actual use and is just a hack to learn about bolt 8.

Server:
```bash
$ python3 ./src/main.py
serving on 03b76bd6824a1966998a1308072b4e5b4eaf2fc935be0f8d85b613abe21dbccbf8@127.0.0.1:8080
```

Client:
```bash
echo "hello world!" | python3 ./src/main.py 03b76bd6824a1966998a1308072b4e5b4eaf2fc935be0f8d85b613abe21dbccbf8@127.0.0.1:8080
```
or
```bash
python3 ./src/main.py ~/Videos/largeVideo.mp4 03b76bd6824a1966998a1308072b4e5b4eaf2fc935be0f8d85b613abe21dbccbf8@127.0.0.1:8080
```
