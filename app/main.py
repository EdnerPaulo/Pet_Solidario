import os
import xml.etree.ElementTree as ET
from flask import Flask, render_template, request, jsonify, redirect
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Carrega credenciais do arquivo .env local
load_dotenv()

app = Flask(__name__, template_folder="../templates", static_folder="../static")

# Configuração e higienização da string de conexão do Neon.tech para o SQLAlchemy Puro
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://neondb_owner:npg_Hgdx96wbONcA@ep-divine-sunset-aqvyhf3j-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Inicializa o mecanismo de conexão (Engine) do SQLAlchemy
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==============================================================================
# MODELOS DE MODELAGEM DO BANCO DE DADOS (Padrão Sprint 2 do Grupo)
# ==============================================================================

class Animal(Base):
    __tablename__ = 'animais'
    animal_id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    especie = Column(String(50), nullable=False)
    idade = Column(String(50), nullable=False)
    descricao = Column(Text, nullable=True)

    def to_dict(self):
        return {"id": self.animal_id, "nome": self.nome, "especie": self.especie, "idade": self.idade, "descricao": self.descricao}

class Estoque(Base):
    __tablename__ = 'estoque'
    estoque_id = Column(Integer, primary_key=True, autoincrement=True)
    item = Column(String(100), nullable=False)
    quantidade = Column(String(50), nullable=False)
    status = Column(String(100), nullable=False)

    def to_dict(self):
        return {"id": self.estoque_id, "item": self.item, "quantidade": self.quantidade, "status": self.status}

# Cria as tabelas automaticamente no Neon se não existirem
Base.metadata.create_all(bind=engine)

# Helper para ler a mensagem do arquivo XML dinamicamente
def obter_log_xml():
    try:
        caminho_xml = os.path.join(os.path.dirname(__file__), '../config.xml')
        tree = ET.parse(caminho_xml)
        root = tree.getroot()
        return root.find('notificacao').text.strip()
    except Exception:
        return "Sistema iniciado com sucesso. Estoque sincronizado."

# ==============================================================================
# ROTAS DO FRONTEND (Renderização Jinja2)
# ==============================================================================

@app.route('/')
def index():
    session = SessionLocal()
    try:
        animais = session.query(Animal).order_by(Animal.animal_id.desc()).all()
        lista_animais = [a.to_dict() for a in animais]
    except Exception as e:
        print(f"Erro ao buscar pets: {e}")
        lista_animais = []
    finally:
        session.close()
        
    return render_template('index.html', animais=lista_animais)

@app.route('/admin')
def admin():
    session = SessionLocal()
    try:
        itens_estoque = session.query(Estoque).all()
        total_animais = session.query(Animal).count()
        
        lista_estoque = [i.to_dict() for i in itens_estoque]
        total_itens = len(lista_estoque)
        alertas_count = sum(1 for item in lista_estoque if "Atenção" in item['status'])
    except Exception as e:
        print(f"Erro no painel administrativo: {e}")
        lista_estoque = []
        total_animais = 0
        total_itens = 0
        alertas_count = 0
    finally:
        session.close()

    log_mensagem = obter_log_xml()

    return render_template(
        'admin.html', 
        estoque=lista_estoque, 
        total_animais=total_animais, 
        total_itens=total_itens,
        alertas=alertas_count,
        log_xml=log_mensagem
    )

# ==============================================================================
# ENDPOINTS DA API REST (Cadastro via Formulários Modais e Retornos JSON)
# ==============================================================================

@app.route('/api/animais', methods=['GET', 'POST'])
def api_animais():
    session = SessionLocal()
    if request.method == 'POST':
        dados = request.get_json() if request.is_json else request.form
        novo_pet = Animal(
            nome=dados.get('nome'),
            especie=dados.get('especie'),
            idade=dados.get('idade'),
            descricao=dados.get('descricao')
        )
        try:
            session.add(novo_pet)
            session.commit()
            if request.is_json:
                return jsonify({"status": "sucesso", "animal": novo_pet.to_dict()}), 201
            return redirect('/')
        except Exception as e:
            session.rollback()
            return jsonify({"erro": str(e)}), 500
        finally:
            session.close()

    animais = session.query(Animal).all()
    session.close()
    return jsonify([a.to_dict() for a in animais])

@app.route('/api/estoque', methods=['POST'])
def api_estoque():
    session = SessionLocal()
    dados = request.get_json() if request.is_json else request.form
    novo_item = Estoque(
        item=dados.get('item'),
        quantidade=dados.get('quantidade'),
        status=dados.get('status', 'Estoque Regular')
    )
    try:
        session.add(novo_item)
        session.commit()
        if request.is_json:
            return jsonify({"status": "sucesso", "item": novo_item.to_dict()}), 201
        return redirect('/admin')
    except Exception as e:
        session.rollback()
        return jsonify({"erro": str(e)}), 500
    finally:
        session.close()

if __name__ == '__main__':
    app.config['SECRET_KEY'] = 'dev-key-eniac'
    app.run(debug=True)
