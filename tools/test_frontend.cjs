const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { JSDOM } = require('jsdom');

function setup() {
    const dom = new JSDOM(`<form id="alvina-request-form"><select id="alvina-branch"><option value="1">Una</option><option value="2">Dos</option></select><select id="alvina-category"><option>Comerciales</option><option>Útiles de limpieza</option></select><input id="alvina-catalog"><input id="alvina-lines"><table><tbody id="alvina-products"></tbody></table><p id="alvina-empty" hidden></p><button type="submit">Enviar requerimiento</button></form>`, { runScripts: 'outside-only' });
    const w = dom.window, d = w.document;
    d.getElementById('alvina-catalog').value = JSON.stringify({
        1: [{ id: 1, name: 'Agua', category: 'Comerciales', uom: 'Unidades', rounding: 1 },
            { id: 2, name: 'Jabón', category: 'Útiles de limpieza', uom: 'Unidades', rounding: 1 }],
        2: [{ id: 3, name: 'Otro producto', category: 'Comerciales', uom: 'Unidades', rounding: 1 }],
    });
    w.eval(readFileSync(resolve(__dirname, '../alvina_branch_requisition/static/src/form.js'), 'utf8'));
    d.dispatchEvent(new w.Event('DOMContentLoaded'));
    let alerts = 0;
    w.alert = () => alerts++;
    return { w, d, alerts: () => alerts, dom,
        quantity(value) {
            const input = d.querySelector('#alvina-products input');
            input.value = value; input.dispatchEvent(new w.Event('input'));
        },
        category(value) {
            const select = d.getElementById('alvina-category');
            select.value = value; select.dispatchEvent(new w.Event('change'));
        },
        submit() {
            const event = new w.Event('submit', { cancelable: true });
            d.getElementById('alvina-request-form').dispatchEvent(event);
            return event;
        },
    };
}

test('cantidades persisten entre categorías y se envían juntas', () => {
    const x = setup();
    assert.equal(x.d.querySelector('#alvina-products input').value, '0');
    x.quantity('3'); x.category('Útiles de limpieza'); x.quantity('5');
    x.category('Comerciales');
    assert.equal(x.d.querySelector('#alvina-products input').value, '3');
    x.submit();
    assert.deepEqual(JSON.parse(x.d.getElementById('alvina-lines').value), [{ id: 1, qty: '3' }, { id: 2, qty: '5' }]);
    assert.ok(x.d.querySelector('button').disabled);
    x.dom.window.close();
});

test('cambiar sucursal limpia cantidades y cambia el catálogo', () => {
    const x = setup(); x.quantity('7');
    const branch = x.d.getElementById('alvina-branch');
    branch.value = '2'; branch.dispatchEvent(new x.w.Event('change'));
    assert.match(x.d.getElementById('alvina-products').textContent, /Otro producto/);
    assert.equal(x.d.querySelector('#alvina-products input').value, '0');
    assert.ok(x.submit().defaultPrevented);
    x.dom.window.close();
});

test('cantidades negativas conservadas en otra categoría bloquean envío', () => {
    const x = setup(); x.quantity('-1'); x.category('Útiles de limpieza'); x.quantity('2');
    assert.ok(x.submit().defaultPrevented); assert.equal(x.alerts(), 1);
    assert.equal(x.d.querySelector('button').disabled, false);
    x.dom.window.close();
});

test('borrar una cantidad entre categorías permite enviar los demás productos', () => {
    const x = setup();
    x.quantity('3'); x.category('Útiles de limpieza'); x.quantity('5');
    x.category('Comerciales'); x.quantity(''); x.category('Útiles de limpieza');
    assert.equal(x.submit().defaultPrevented, false);
    assert.deepEqual(JSON.parse(x.d.getElementById('alvina-lines').value), [{ id: 2, qty: '5' }]);
    assert.equal(x.alerts(), 0);
    x.dom.window.close();
});

test('un número incompleto oculto en otra categoría conserva su error', () => {
    const x = setup();
    const input = x.d.querySelector('#alvina-products input');
    input.value = '';
    // jsdom does not simulate the browser's incomplete numeric editor state.
    Object.defineProperty(input, 'validity', { value: { badInput: true } });
    input.dispatchEvent(new x.w.Event('input'));
    x.category('Útiles de limpieza'); x.quantity('2');
    assert.ok(x.submit().defaultPrevented);
    x.category('Comerciales');
    assert.equal(x.d.querySelector('#alvina-products input').validity.customError, true);
    x.quantity('');
    assert.equal(x.submit().defaultPrevented, false);
    assert.deepEqual(JSON.parse(x.d.getElementById('alvina-lines').value), [{ id: 2, qty: '2' }]);
    x.dom.window.close();
});
