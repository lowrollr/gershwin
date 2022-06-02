
from scipy.optimize import minimize

class ScipySolver:
    def __init__(self) -> None:
        self.namespace = dict()
        pass
    
    def parse_function_body(self, s):
        elems = s.split(" ")
    
        for index, item in enumerate(elems):
            if item[0] == 'x': # it's a variable
                # we need to look this up and replace it with either a constant, a variable, or a function call
                var = self.namespace[item]
                if var is not None:
                    elems[index] = str(var)
                else:

                    raise Exception(f"Item {item} not defined!")
                    # var not defined! throw an error
        return " ".join(elems)

    def compile_function(self, fn):
        return eval(compile(fn, "<string>", "eval"))
        
    def parse_message(self, msg):
        try:
            self.namespace.clear()
            eval_vars = []
            states_to_send = dict()
            constants_to_scale = []
            norm_factor = 1
            
            key = msg['key']

            constants = msg['constants']
            for c in constants:
                name = c['var_name']
                value = c['value']
                if name and value: 
                    if name in self.namespace:
                        raise Exception(f"Identifier {name} used twice!")
                    self.namespace[name] = int(value)
                    constants_to_scale.append(name)
                    norm_factor = max(norm_factor, abs(int(value)))
                else:
                    raise Exception("Constant defined improperly: ", c)

            for const_name in constants_to_scale:
                self.namespace[const_name] = self.namespace[const_name] / norm_factor

            variables = msg['variables']
            for v in variables:
                name = v['var_name']
                upper_bound = int(v['upper_bound']) / norm_factor if v.get('upper_bound') != None else None
                lower_bound = int(v['lower_bound']) / norm_factor if v.get('lower_bound') != None else None
                initial_guess = int(v['initial_guess']) / norm_factor if v.get('initial_guess') else 0

                if name:
                    if name in self.namespace:
                        raise Exception(f"Identifier {name} used twice!")
                    self.namespace[name] = f'v[{str(len(eval_vars))}]'
                    eval_vars.append((initial_guess, (lower_bound, upper_bound)))

                    if name in msg['return_states']:
                        states_to_send[name] = self.compile_function(f'lambda v: {self.namespace[name]}')
                else:
                    raise Exception("Variable defined improperly: ", v)

            functions = msg['functions']
            for f in functions:
                name = f.get('var_name')
                body = f.get('body')
                
                
                if name and body:
                    if name in self.namespace:
                        raise Exception(f"Identifier {name} used twice!")
                    self.namespace[name] = self.parse_function_body(body)

                    if name in msg['return_states']:
                        states_to_send[name] = self.compile_function(f'lambda v: {self.namespace[name]}')

                else:
                    raise Exception("Function defined improperly: ", f)

            

            solver_constraints = []
            constraints = msg['constraints']
            for c in constraints:
                body = c['body']
                c_type = c['type']
                if body and c_type:
                    if c_type == 'eq' or c_type == 'ineq':
                        fn = self.compile_function(f'lambda v: {self.parse_function_body(body)}')
                        solver_constraints.append({'type': c_type, 'fun': fn})
                    else:
                        raise Exception(f'Unknown constraint type {c_type}')
                else:
                    raise Exception(f"Constraint defined improperly: ", c)

            tol = pow(10, -1 * len(str(norm_factor)))
            ftol = tol
            to_solve = msg['solve']
            solve_type = to_solve['type']
            if solve_type == 'minimize':
                fn = self.compile_function(f'lambda v: {self.parse_function_body(to_solve["body"])}')
                solution = minimize(fn, 
                            [x[0] for x in eval_vars],
                            tol=tol,
                            method='slsqp',
                            bounds=[x[1] for x in eval_vars],
                            options={'disp': True, 'ftol': ftol, 'maxiter': 1000},
                            constraints=solver_constraints
                            )
                print(solution)
                if solution.success or solution.fun < 0:
                    return {
                        "key": key,
                        "best_inputs": [str(int(x * norm_factor)) for x in solution.x.tolist()],
                        "best_result": str(int(fn(solution.x.tolist()) * norm_factor)),
                        "end_states": {name: str(int(fn(solution.x.tolist()) * norm_factor)) for name, fn in states_to_send.items()}
                    }
                else:
                    return {
                        "key": key,
                        "best_inputs": [],
                        "best_result": [],
                        "end_states": []
                    }


            elif solve_type == 'maximize':
                fn = self.compile_function(f'lambda v: {self.parse_function_body("-1 * ( " + to_solve["body"] + " )")}')
                solution = minimize(fn, 
                            [0],
                            tol=tol,
                            method='slsqp',
                            bounds=[x[1] for x in eval_vars],
                            options={'disp': True, 'ftol': ftol, 'maxiter': 1000},
                            constraints=solver_constraints
                            )
                print(solution)
                if solution.success or solution.fun < 0:
                    return {
                        "key": key,
                        "best_inputs": [str(int(x * norm_factor)) for x in solution.x.tolist()],
                        "best_result": str(int(fn(solution.x.tolist()) * -1 * norm_factor)),
                        "fn_results": {name: str(int(fn(solution.x.tolist()) * norm_factor)) for name, fn in states_to_send.items()}
                    }
                    
                else:
                    return {
                        "key": key,
                        "best_inputs": [],
                        "best_result": [],
                        "fn_results": []
                    }


            else:
                raise Exception(f"Unknown solve type {solve_type}")
        except Exception as e:
            print('message', msg)
            print('exception', e)
            raise e
