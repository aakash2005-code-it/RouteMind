from app import app
if __name__=='__main__':
 print('RouteMind dashboard: http://127.0.0.1:5055')
 app.run(host='127.0.0.1',port=5055,debug=False)
