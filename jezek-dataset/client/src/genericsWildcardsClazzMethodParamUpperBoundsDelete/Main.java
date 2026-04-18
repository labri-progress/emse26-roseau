package genericsWildcardsClazzMethodParamUpperBoundsDelete;

import java.util.ArrayList;

import testing_lib.genericsWildcardsClazzMethodParamUpperBoundsDelete.GenericsWildcardsClazzMethodParamUpperBoundsDelete;

public class Main extends GenericsWildcardsClazzMethodParamUpperBoundsDelete {

	public static void main(String[] args) {
		GenericsWildcardsClazzMethodParamUpperBoundsDelete constr = new GenericsWildcardsClazzMethodParamUpperBoundsDelete();
		ArrayList<Number> param1 = new ArrayList<Number>();
		constr.method1(param1);
	}

	@Override
	public void method1(ArrayList<? extends Number> param1) {
		
	}
}
